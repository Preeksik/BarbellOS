"""Trening (etap 4, 25.11.2026): plan AMP 2027 przeniesiony ze starego pliku HTML.

Wszystko liczy serwer (`app/core/season.py`, `app/core/training.py`): daty sesji, ciężary
z TM, talerze, e1RM, status sesji, „ostatnio" i sugestie TM. Telefon wyświetla i zbiera
wpisy. Zapisy wpisów i sesji są idempotentne (PUT z kluczem sesji i indeksem ćwiczenia),
bo mogą czekać w kolejce offline (AGENTS.md, zasada 5).
"""

import datetime as dt
import re
from collections.abc import Mapping
from functools import cached_property
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core import meet
from app.core import season as core
from app.core.training import attempts_for, round_to_step
from app.db.models import Plan, PlanSettings, SessionLog, SetLog, utcnow
from app.db.session import get_db

router = APIRouter(prefix="/api/training", tags=["training"], dependencies=[Depends(require_user)])

# Klucz sesji ze starego pliku: tydzień (z „b" dla powtórki) i kod dnia.
SESSION_KEY = re.compile(r"^t\d{2}b?-[A-Z0-9]{1,8}$")
LIFT_NAMES = {"S": "przysiad", "B": "ława", "D": "martwy"}


# ---------------------------------------------------------------- kontrakt


class EntryIn(BaseModel):
    """Wpis jednego ćwiczenia sesji (jak w starym pliku: jeden na ćwiczenie)."""

    kg: float | None = Field(default=None, ge=0, le=1000)
    reps: float | None = Field(default=None, ge=0, le=1000)  # akcesoria: także minuty
    rpe: float | None = Field(default=None, ge=0, le=10)
    done: bool = False
    ok: Literal["y", "n"] | None = None  # podejście zaliczone albo spalone


class EntryOut(EntryIn):
    pass


class SessionIn(BaseModel):
    gym: str | None = Field(default=None, max_length=64)
    bodyweight: float | None = Field(default=None, gt=20, lt=400)
    note: str | None = Field(default=None, max_length=5000)


class EquipmentIn(BaseModel):
    """Sprzęt na siłowni: od niego zależą talerze na stronę sztangi."""

    plates_25: bool = True  # bez talerzy 25 kg liczymy od 20 kg
    collars: bool = False  # zaciski 2 × 2,5 kg


class EquipmentOut(EquipmentIn):
    has_plan: bool
    plan_name: str | None = None  # wgrany plan (Profil pokazuje go przy imporcie)


class LastOut(BaseModel):
    kg: float
    reps: float | None
    rpe: float | None
    date: dt.date  # kiedy zapisano (jak w starym pliku), a bez znacznika: data sesji
    gym: str


class ExerciseOut(BaseModel):
    index: int
    name: str
    lift: str | None
    kind: str  # sets | single | acc | att
    tier: str  # main | var | acc
    sets: int | None
    reps: str | None  # liczba dla bojów, tekst dla akcesoriów („10/str.")
    percent_tm: float | None
    rpe: str | None  # tekst, bo bywa zakresem („8.5-9")
    weight_hint: str | None
    attempt: int | None
    cue: str | None
    load: float | None  # ciężar z planu (z TM albo stały)
    plates: list[float] | None  # talerze na stronę dla `load`
    entry: EntryOut
    e1rm: float | None  # z wpisu, zaokrąglony do 2,5 kg
    last: LastOut | None  # akcesoria: ostatni wpis tego ćwiczenia


class ThirdHint(BaseModel):
    """Trzecie podejście po drugim: failed | rules | need_rpe | limit | next."""

    kind: Literal["failed", "rules", "need_rpe", "limit", "next"]
    kg: float | None = None
    rpe: float | None = None


class SheetLift(BaseModel):
    lift: str
    max: float  # maks do podejść (zaokrąglony do 2,5 kg)
    from_singles: bool  # z singli albo z TM fazy zastępczej
    fallback_phase: int
    first: float
    second: float
    third: tuple[float, float]  # przedział trzeciego podejścia
    hint: ThirdHint


class SheetOut(BaseModel):
    """Arkusz podejść na teście albo zawodach: plan, podpowiedzi i wynik."""

    context: Literal["test", "meet"]
    lifts: list[SheetLift]
    best: dict[str, float | None]
    total: float | None
    gl: float | None
    bodyweight: float


class SessionOut(BaseModel):
    key: str
    code: str
    title: str
    date: dt.date
    minutes: int | None
    days_before_meet: int | None
    holiday: str | None
    note: str | None  # wskazówka z planu
    status: Literal["none", "part", "done"]
    gym: str | None
    bodyweight: float | None
    log_note: str | None  # notatka użytkownika
    exercises: list[ExerciseOut]
    sheet: SheetOut | None = None  # tylko sesje z podejściami


class TmSuggestion(BaseModel):
    lift: str
    kg: float


class BannerOut(BaseModel):
    """Pierwszy tydzień nowej fazy: obecne TM i podpowiedź z dziennika."""

    phase_name: str
    suggestions: list[TmSuggestion]


class WeekOut(BaseModel):
    index: int
    n: int
    key: str
    block_name: str
    focus: str | None
    start: dt.date
    end: dt.date
    repeat_of: int | None
    phase: int
    tm: dict[str, float]
    banner: BannerOut | None
    sessions: list[SessionOut]
    gyms: list[str]  # znane siłownie, od ostatnio odwiedzonej


class WeekSummary(BaseModel):
    index: int
    n: int
    key: str
    block_name: str
    plate: int | None  # kolor krążka na osi sezonu
    label: str | None  # TEST | AMP
    start: dt.date
    end: dt.date
    repeat_of: int | None
    done: int
    total: int
    holidays: list[str]  # święta w dniach treningowych tego tygodnia


class Countdown(BaseModel):
    days: int  # 0 = dziś
    label: str


class Position(BaseModel):
    week: int
    day: int
    rest: bool  # dziś wolne, pokazany najbliższy trening


class SeasonGroup(BaseModel):
    """Opis części sezonu (np. jesień do testu) z pliku planu."""

    title: str
    text: str
    last_week: int | None = None  # ostatni tydzień tej części; brak = do końca


class SeasonOut(BaseModel):
    plan_name: str | None  # None: planu jeszcze nie wgrano
    headline: str | None
    countdowns: list[Countdown]
    position: Position | None
    current_week: int | None
    weeks: list[WeekSummary]
    groups: list[SeasonGroup] = []


class ImportIn(BaseModel):
    """Plan z pliku i (opcjonalnie) dziennik oraz ustawienia ze starego pliku HTML."""

    plan: dict[str, Any]
    settings: dict[str, Any] | None = None
    logs: dict[str, Any] | None = None


class ImportOut(BaseModel):
    plan_name: str
    weeks: int
    sessions: int
    imported_sessions: int
    skipped: list[str]


# ---------------------------------------------------------------- dane


class Loaded:
    """Plan, ustawienia i dziennik w kształcie, którego używa `app.core.season`."""

    def __init__(self, db: Session):
        plan = db.scalars(select(Plan).order_by(Plan.id)).first()
        if plan is None:
            raise HTTPException(404, "Plan treningowy nie jest jeszcze wgrany.")
        self.plan_row = plan
        self.plan: Mapping = plan.data
        self.settings = db.get(PlanSettings, plan.id) or PlanSettings(
            plan_id=plan.id, tm={}, adj={}, collars=False
        )
        meta = self.plan["meta"]
        self.meet = self.settings.meet_date or dt.date.fromisoformat(meta["default_meet_date"])
        self.season = core.build_season(self.plan, self.meet, self.settings.adj)
        self.logs: dict[str, dict] = {}
        for log in db.scalars(select(SessionLog).where(SessionLog.plan_id == plan.id)):
            self.logs[log.session_key] = {
                "entries": {},
                "gym": log.gym,
                "bodyweight": log.bodyweight,
                "note": log.note,
                "at": log.updated_at,
            }
        for row in db.scalars(select(SetLog).where(SetLog.plan_id == plan.id)):
            log = self.logs.setdefault(row.session_key, {"entries": {}, "at": None})
            log["entries"][row.ex_index] = _entry_dict(row)

    @cached_property
    def gyms(self) -> list[str]:
        return core.known_gyms(self.season, self.logs)

    @cached_property
    def points(self) -> list[core.LiftPoint]:
        return core.lift_points(self.season, self.logs)

    def default_bodyweight(self, context: str) -> float:
        defaults = (self.plan.get("attempts") or {}).get("default_bodyweight") or {}
        weight_class = (self.plan.get("meta") or {}).get("weight_class_kg")
        return float(defaults.get(context) or weight_class or meet.DEFAULT_BODYWEIGHT)

    def context_max(self, context: str, lift: str) -> tuple[float, bool, int]:
        """Maks do podejść: (wartość, czy z singli, faza zastępcza)."""
        attempts = self.plan.get("attempts") or {}
        weeks = (attempts.get("context_weeks") or {}).get(context) or []
        phase = int((attempts.get("fallback_phase") or {}).get(context) or 1)
        value, from_singles = meet.context_max(self.points, weeks, self.tm(phase, lift), lift)
        return value, from_singles, phase

    def tm(self, phase: int, lift: str) -> float:
        return core.tm_value(self.plan, self.settings.tm, phase, lift)

    def slot(self, key: str) -> core.SessionSlot:
        for slot in core.all_sessions(self.season):
            if slot.key == key:
                return slot
        raise HTTPException(404, f"Nie ma sesji {key} w planie.")


def _entry_dict(row: SetLog) -> dict:
    out: dict[str, Any] = {"kg": row.kg, "reps": row.reps, "rpe": row.rpe}
    if row.done:
        out["done"] = True
    if row.ok:
        out["ok"] = row.ok
    return out


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _exercise_out(data: Loaded, week: core.WeekSlot, slot: core.SessionSlot, i: int, ex) -> dict:
    entries = (data.logs.get(slot.key) or {}).get("entries") or {}
    entry = entries.get(i) or {}
    lift = ex.get("lift")
    load = core.planned_load(ex, data.tm(week.phase, lift) if lift else 0.0)
    e1 = core.entry_e1rm(ex, entry)
    last = None
    if ex.get("kind") == "acc":
        gym = (data.logs.get(slot.key) or {}).get("gym") or (data.gyms[0] if data.gyms else "")
        found = core.last_result(data.season, data.logs, ex["name"], gym, slot)
        if found:
            last = LastOut(
                kg=found["kg"],
                reps=found["reps"],
                rpe=found["rpe"],
                date=found["shown"],
                gym=found["gym"],
            )
    cue = ((data.plan.get("exercises") or {}).get(ex["name"]) or {}).get("cue")
    return {
        "index": i,
        "name": ex["name"],
        "lift": lift,
        "kind": ex.get("kind") or "acc",
        "tier": ex.get("tier") or "acc",
        "sets": ex.get("sets") if isinstance(ex.get("sets"), int) else None,
        "reps": _text(ex.get("reps")),
        "percent_tm": ex.get("percent_tm"),
        "rpe": _text(ex.get("rpe")),
        "weight_hint": _text(ex.get("weight_hint")),
        "attempt": ex.get("attempt"),
        # Wskazówka z planu dla tej pozycji ma pierwszeństwo przed ogólną (jak w starym pliku).
        "cue": ex.get("note") or cue,
        "load": load,
        "plates": (
            core.plates_for(
                load, data.settings.collars, 25 if data.settings.plates_25 is not False else 20
            )
            if load is not None
            else None
        ),
        "entry": EntryOut(
            kg=core.number(entry.get("kg")),
            reps=core.number(entry.get("reps")),
            rpe=core.number(entry.get("rpe")),
            done=bool(entry.get("done")),
            ok=entry.get("ok") if entry.get("ok") in ("y", "n") else None,
        ),
        "e1rm": round_to_step(e1) if e1 else None,
        "last": last,
    }


def _session_out(data: Loaded, week: core.WeekSlot, slot: core.SessionSlot) -> SessionOut:
    log = data.logs.get(slot.key) or {}
    exercises = slot.day.get("exercises") or []
    return SessionOut(
        key=slot.key,
        code=slot.day["code"],
        title=slot.day.get("title") or slot.day["code"],
        date=slot.date,
        minutes=slot.day.get("minutes"),
        days_before_meet=slot.day.get("days_before_meet"),
        holiday=(data.plan.get("holidays") or {}).get(slot.date.isoformat()),
        note=slot.day.get("note"),
        status=core.session_status(exercises, log.get("entries") or {}),
        gym=log.get("gym"),
        bodyweight=log.get("bodyweight"),
        log_note=log.get("note"),
        exercises=[
            ExerciseOut(**_exercise_out(data, week, slot, i, ex)) for i, ex in enumerate(exercises)
        ],
        sheet=_sheet(data, slot) if any(e.get("kind") == "att" for e in exercises) else None,
    )


def _sheet(data: Loaded, slot: core.SessionSlot) -> SheetOut:
    """Arkusz podejść (`renderSheet`): plan z maksu, trzecie po drugim, wynik i GL."""
    context: Literal["test", "meet"] = "test" if slot.day["code"] == "TEST" else "meet"
    exercises = slot.day.get("exercises") or []
    log = data.logs.get(slot.key) or {}
    entries = log.get("entries") or {}
    lifts = []
    for lift in core.LIFTS:
        value, from_singles, phase = data.context_max(context, lift)
        plan = attempts_for(value, lift)
        second = next(
            (
                i
                for i, e in enumerate(exercises)
                if e.get("kind") == "att" and e.get("lift") == lift and e.get("attempt") == 2
            ),
            None,
        )
        hint = meet.third_hint(entries.get(second) if second is not None else None, lift)
        lifts.append(
            SheetLift(
                lift=lift,
                max=round_to_step(value),
                from_singles=from_singles,
                fallback_phase=phase,
                first=plan["first"],
                second=plan["second"],
                third=plan["third"],
                hint=ThirdHint(**hint),
            )
        )
    result = meet.sheet_result(
        exercises, entries, core.number(log.get("bodyweight")), data.default_bodyweight(context)
    )
    return SheetOut(
        context=context,
        lifts=lifts,
        best=result["best"],
        total=result["total"],
        gl=result["gl"],
        bodyweight=result["bodyweight"],
    )


def _block_name(plan: Mapping, block: str) -> str:
    return ((plan.get("blocks") or {}).get(block) or {}).get("name") or block


def _banner(data: Loaded, index: int) -> BannerOut | None:
    week = data.season[index]
    first = next(i for i, w in enumerate(data.season) if w.phase == week.phase)
    if week.phase <= 1 or first != index:
        return None
    points = core.lift_points(data.season, data.logs)
    suggestions = []
    for lift in core.LIFTS:
        value = core.tm_suggestion(points, week.phase, lift, data.tm(week.phase, lift))
        if value is not None:
            suggestions.append(TmSuggestion(lift=lift, kg=value))
    phase_name = (data.plan.get("phases") or {}).get(str(week.phase)) or f"Faza {week.phase}"
    return BannerOut(phase_name=phase_name, suggestions=suggestions)


def _days_word(n: int) -> str:
    return "dzień" if n == 1 else "dni"


def _short_date(day: dt.date) -> str:
    return f"{day.day}.{day.month:02d}"


def _header(data: Loaded, today: dt.date) -> tuple[str, list[Countdown]]:
    season = data.season
    current = core.current_week(season, today)
    if today < season[0].start:
        line = f"Start {_short_date(season[0].start)}"
    elif current is not None:
        week = season[current]
        line = (
            f"Tydzień {week.n} z {len(season)} · {_block_name(data.plan, week.template['block'])}"
        )
    elif today > season[-1].end:
        line = "Sezon zakończony"
    else:
        line = "Przerwa między blokami"
    countdowns = []
    meta = data.plan["meta"]
    if meta.get("test_date"):
        test = dt.date.fromisoformat(meta["test_date"])
        days = (test - today).days
        if days > 0:
            countdowns.append(
                Countdown(days=days, label=f"{_days_word(days)} do testu {_short_date(test)}")
            )
        elif days == 0:
            countdowns.append(Countdown(days=0, label="test"))
    days = (data.meet - today).days
    confirmed = data.settings.meet_date is not None and data.meet.isoformat() != meta.get(
        "default_meet_date"
    )
    when = _short_date(data.meet) if confirmed else f"ok. {_short_date(data.meet)}"
    if days > 0:
        countdowns.append(Countdown(days=days, label=f"{_days_word(days)} do zawodów ({when})"))
    elif days == 0:
        countdowns.append(Countdown(days=0, label="zawody"))
    return line, countdowns


# ---------------------------------------------------------------- odczyt


@router.get("/season", response_model=SeasonOut)
def get_season(today: dt.date, db: Session = Depends(get_db)) -> SeasonOut:
    """Oś sezonu, nagłówek i sesja do pokazania. `today` to data z telefonu."""
    try:
        data = Loaded(db)
    except HTTPException as exc:
        if exc.status_code == 404:
            return SeasonOut(
                plan_name=None,
                headline=None,
                countdowns=[],
                position=None,
                current_week=None,
                weeks=[],
            )
        raise
    week, day, rest = core.auto_locate(data.season, data.logs, today, utcnow())
    headline, countdowns = _header(data, today)
    return SeasonOut(
        plan_name=data.plan_row.name,
        headline=headline,
        countdowns=countdowns,
        position=Position(week=week, day=day, rest=rest),
        current_week=core.current_week(data.season, today),
        weeks=[
            WeekSummary(
                index=i,
                n=w.n,
                key=w.key,
                block_name=_block_name(data.plan, w.template["block"]),
                plate=w.template.get("intensity_plate_kg"),
                label=w.template.get("label"),
                start=w.start,
                end=w.end,
                repeat_of=w.repeat_of,
                done=sum(
                    core.session_status(
                        s.day.get("exercises") or [],
                        (data.logs.get(s.key) or {}).get("entries") or {},
                    )
                    == "done"
                    for s in w.sessions
                ),
                total=len(w.sessions),
                holidays=[
                    name
                    for s in w.sessions
                    if (name := (data.plan.get("holidays") or {}).get(s.date.isoformat()))
                ],
            )
            for i, w in enumerate(data.season)
        ],
        groups=[
            SeasonGroup(**g)
            for g in ((data.plan.get("notes") or {}).get("season") or [])
            if isinstance(g, Mapping) and g.get("title")
        ],
    )


@router.get("/week/{index}", response_model=WeekOut)
def get_week(index: int, db: Session = Depends(get_db)) -> WeekOut:
    data = Loaded(db)
    if not 0 <= index < len(data.season):
        raise HTTPException(404, "Nie ma takiego tygodnia.")
    week = data.season[index]
    block = (data.plan.get("blocks") or {}).get(week.template["block"]) or {}
    return WeekOut(
        index=index,
        n=week.n,
        key=week.key,
        block_name=_block_name(data.plan, week.template["block"]),
        focus=week.template.get("note") or block.get("focus"),
        start=week.start,
        end=week.end,
        repeat_of=week.repeat_of,
        phase=week.phase,
        tm={lift: data.tm(week.phase, lift) for lift in core.LIFTS},
        banner=_banner(data, index),
        sessions=[_session_out(data, week, slot) for slot in week.sessions],
        gyms=data.gyms,
    )


# ---------------------------------------------------------------- zapis


def _session_row(db: Session, plan_id: int, key: str) -> SessionLog:
    row = db.get(SessionLog, (plan_id, key))
    if row is None:
        row = SessionLog(plan_id=plan_id, session_key=key)
        db.add(row)
    return row


@router.put("/sessions/{key}/entries/{index}", status_code=204)
def put_entry(key: str, index: int, body: EntryIn, db: Session = Depends(get_db)) -> Response:
    """Wpis ćwiczenia w całości. Pusty wpis usuwa wiersz. Powtórka niczego nie zmienia."""
    data = Loaded(db)
    slot = data.slot(key)
    if not 0 <= index < len(slot.day.get("exercises") or []):
        raise HTTPException(404, "Nie ma takiego ćwiczenia w tej sesji.")
    plan_id = data.plan_row.id
    row = db.get(SetLog, (plan_id, key, index))
    empty = body.kg is None and body.reps is None and body.rpe is None
    if empty and not body.done and body.ok is None:
        if row is not None:
            db.delete(row)
    else:
        if row is None:
            row = SetLog(plan_id=plan_id, session_key=key, ex_index=index)
            db.add(row)
        row.kg, row.reps, row.rpe = body.kg, body.reps, body.rpe
        row.done, row.ok = body.done, body.ok
    # Znacznik sesji („ostatnio", kolejna sesja po zapisie) zmienia się przy każdym wpisie.
    _session_row(db, plan_id, key).updated_at = utcnow()
    db.commit()
    return Response(status_code=204)


@router.put("/sessions/{key}", status_code=204)
def put_session(key: str, body: SessionIn, db: Session = Depends(get_db)) -> Response:
    """Siłownia, masa ciała i notatka sesji w całości."""
    data = Loaded(db)
    data.slot(key)
    row = _session_row(db, data.plan_row.id, key)
    row.gym = (body.gym or "").strip() or None
    row.bodyweight = body.bodyweight
    row.note = (body.note or "").strip() or None
    row.updated_at = utcnow()
    db.commit()
    return Response(status_code=204)


@router.get("/equipment", response_model=EquipmentOut)
def get_equipment(db: Session = Depends(get_db)) -> EquipmentOut:
    plan = db.scalars(select(Plan).order_by(Plan.id)).first()
    settings = db.get(PlanSettings, plan.id) if plan else None
    return EquipmentOut(
        has_plan=plan is not None,
        plan_name=plan.name if plan else None,
        plates_25=settings.plates_25 if settings else True,
        collars=settings.collars if settings else False,
    )


@router.put("/equipment", status_code=204)
def put_equipment(body: EquipmentIn, db: Session = Depends(get_db)) -> Response:
    """Talerze 25 kg i zaciski w całości. Powtórka niczego nie zmienia."""
    plan = db.scalars(select(Plan).order_by(Plan.id)).first()
    if plan is None:
        raise HTTPException(404, "Najpierw wgraj plan treningowy.")
    settings = db.get(PlanSettings, plan.id)
    if settings is None:
        settings = PlanSettings(plan_id=plan.id, tm={}, adj={})
        db.add(settings)
    settings.plates_25, settings.collars = body.plates_25, body.collars
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- import


def _old_entry(raw: object) -> dict | None:
    """Wpis w formacie starego pliku: { kg, reps, rpe, done, ok }."""
    if not isinstance(raw, Mapping):
        return None
    try:
        entry = EntryIn(
            kg=core.number(raw.get("kg")),
            reps=core.number(raw.get("reps")),
            rpe=core.number(raw.get("rpe")),
            done=bool(raw.get("done")),
            ok=raw.get("ok") if raw.get("ok") in ("y", "n") else None,
        )
    except ValueError:
        return None
    return entry.model_dump()


def _old_time(value: object) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


@router.put("/plan", response_model=ImportOut)
def put_plan(body: ImportIn, db: Session = Depends(get_db)) -> ImportOut:
    """Wgrywa plan (zastępuje obecny) i opcjonalnie dziennik ze starego pliku HTML.

    Sesje z pliku zastępują te same sesje w bazie; pozostałe zostają. Wymaga sieci,
    więc nie idzie przez kolejkę offline.
    """
    if errors := core.plan_errors(body.plan):
        raise HTTPException(422, " ".join(errors))
    name = str((body.plan.get("meta") or {}).get("name") or "Plan treningowy")[:128]
    plan = db.scalars(select(Plan).order_by(Plan.id)).first()
    if plan is None:
        plan = Plan(name=name, data=body.plan)
        db.add(plan)
        db.flush()
    else:
        plan.name, plan.data = name, body.plan
    settings = db.get(PlanSettings, plan.id)
    if settings is None:
        settings = PlanSettings(plan_id=plan.id, tm={}, adj={}, collars=False)
        db.add(settings)
    old = body.settings or {}
    if isinstance(old.get("tm"), Mapping):
        settings.tm = {
            str(phase): {
                lift: float(v)
                for lift, v in values.items()
                if lift in core.LIFTS and isinstance(v, int | float) and v > 0
            }
            for phase, values in old["tm"].items()
            if isinstance(values, Mapping)
        }
    if isinstance(old.get("adj"), Mapping):
        settings.adj = {
            "ins": [k for k in old["adj"].get("ins") or [] if isinstance(k, str)],
            "rem": [k for k in old["adj"].get("rem") or [] if isinstance(k, str)],
        }
    if old.get("meet"):
        try:
            meet = dt.date.fromisoformat(str(old["meet"]))
        except ValueError:
            meet = None
        default = (body.plan.get("meta") or {}).get("default_meet_date")
        settings.meet_date = None if meet is None or meet.isoformat() == default else meet
    if isinstance(old.get("collars"), bool):
        settings.collars = old["collars"]
    db.flush()

    data = Loaded(db)
    slots = {s.key: s for s in core.all_sessions(data.season)}
    imported, skipped = 0, []
    for key, raw in (body.logs or {}).items():
        slot = slots.get(key)
        if not SESSION_KEY.match(key) or slot is None or not isinstance(raw, Mapping):
            skipped.append(key)
            continue
        count = len(slot.day.get("exercises") or [])
        db.execute(delete(SetLog).where(SetLog.plan_id == plan.id, SetLog.session_key == key))
        entries = raw.get("e") if isinstance(raw.get("e"), Mapping) else {}
        for index_text, raw_entry in entries.items():
            index = int(index_text) if str(index_text).isdigit() else -1
            entry = _old_entry(raw_entry)
            if not 0 <= index < count or entry is None:
                skipped.append(f"{key}/{index_text}")
                continue
            db.add(SetLog(plan_id=plan.id, session_key=key, ex_index=index, **entry))
        row = _session_row(db, plan.id, key)
        row.gym = (str(raw.get("gym") or "").strip() or None) if raw.get("gym") else None
        bodyweight = core.number(raw.get("bw"))
        row.bodyweight = bodyweight if bodyweight and 20 < bodyweight < 400 else None
        row.note = str(raw.get("note") or "").strip() or None
        row.updated_at = _old_time(raw.get("at")) or utcnow()
        imported += 1
    db.commit()
    return ImportOut(
        plan_name=name,
        weeks=len(data.season),
        sessions=len(slots),
        imported_sessions=imported,
        skipped=skipped,
    )
