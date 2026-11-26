"""Trening, część 2 (26.11.2026): maksy, kalkulator, start, data zawodów i zasady.

Liczby liczy `app/core/meet.py` i `app/core/season.py`. Teksty osobiste (cele, lista
pakowania, zasady planu) pochodzą z pliku planu (`notes`), który nie jest w repo.
"""

import datetime as dt
from collections.abc import Mapping
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.api.training import Loaded
from app.core import meet
from app.core import season as core
from app.core.training import attempts_for, round_to_step
from app.db.session import get_db

router = APIRouter(prefix="/api/training", tags=["training"], dependencies=[Depends(require_user)])


# ---------------------------------------------------------------- teksty z planu


class NoteItem(BaseModel):
    lead: str | None = None  # pogrubiony początek, np. „Przysiad"
    text: str


class NoteBlock(BaseModel):
    type: Literal["p", "list", "table"]
    text: str | None = None
    items: list[NoteItem] = []
    head: list[str] = []
    rows: list[list[str]] = []


class NoteSection(BaseModel):
    title: str | None = None
    blocks: list[NoteBlock] = []


def _blocks(raw: object) -> list[NoteBlock]:
    out = []
    for item in raw if isinstance(raw, list) else []:
        try:
            out.append(NoteBlock.model_validate(item))
        except ValidationError:
            continue
    return out


def _sections(raw: object) -> list[NoteSection]:
    out = []
    for item in raw if isinstance(raw, list) else []:
        try:
            out.append(NoteSection.model_validate(item))
        except ValidationError:
            continue
    return out


def _notes(data: Loaded) -> Mapping:
    notes = data.plan.get("notes")
    return notes if isinstance(notes, Mapping) else {}


# ---------------------------------------------------------------- maksy


class GoalRow(BaseModel):
    label: str
    S: float
    B: float
    D: float
    total: float
    gl: float
    baseline: bool


class TmCell(BaseModel):
    lift: str
    value: float
    default: float
    manual: bool  # wpisane ręcznie
    suggestion: float | None  # z dziennika


class PhaseRow(BaseModel):
    phase: int
    name: str
    first_week: int
    last_week: int
    start: dt.date
    total: float
    lifts: list[TmCell]


class PointOut(BaseModel):
    date: dt.date
    lift: str
    kg: float
    rpe: float
    e1rm: float  # dokładny, do wykresu
    e1rm_rounded: float  # do 2,5 kg, do tabeli
    kind: Literal["single", "att"]


class MaxesOut(BaseModel):
    goals_title: str
    goals_intro: list[NoteBlock]
    goals: list[GoalRow]
    goals_after: list[NoteSection]
    tm_intro: list[NoteBlock]
    phases: list[PhaseRow]
    points: list[PointOut]
    # Oś wykresu: od startu planu do zawodów, z kreską testu i zawodów.
    start_date: dt.date
    test_date: dt.date | None
    meet_date: dt.date
    meet_name: str


class TmIn(BaseModel):
    """TM jednej fazy w całości; brak wartości = wartość domyślna z planu."""

    S: float | None = Field(default=None, gt=0, le=600)
    B: float | None = Field(default=None, gt=0, le=600)
    D: float | None = Field(default=None, gt=0, le=600)


@router.get("/maxes", response_model=MaxesOut)
def get_maxes(db: Session = Depends(get_db)) -> MaxesOut:
    data = Loaded(db)
    notes = _notes(data).get("maxes") or {}
    points = data.points
    phases_info: dict[int, list[core.WeekSlot]] = {}
    for week in data.season:
        phases_info.setdefault(week.phase, []).append(week)
    names = data.plan.get("phases") or {}
    overrides = data.settings.tm or {}
    phases = []
    for phase, weeks in sorted(phases_info.items()):
        cells = []
        for lift in core.LIFTS:
            value = data.tm(phase, lift)
            manual = isinstance((overrides.get(str(phase)) or {}).get(lift), int | float)
            cells.append(
                TmCell(
                    lift=lift,
                    value=value,
                    default=meet.tm_default(data.plan, overrides, phase, lift),
                    manual=manual,
                    suggestion=core.tm_suggestion(points, phase, lift, value),
                )
            )
        phases.append(
            PhaseRow(
                phase=phase,
                name=names.get(str(phase)) or f"Faza {phase}",
                first_week=weeks[0].n,
                last_week=weeks[-1].n,
                start=weeks[0].start,
                total=sum(c.value for c in cells),
                lifts=cells,
            )
        )
    meta = data.plan["meta"]
    return MaxesOut(
        goals_title=notes.get("goals_title") or "Cele",
        goals_intro=_blocks(notes.get("goals_intro")),
        goals=[
            GoalRow(**row)
            for row in meet.goal_rows(
                [g for g in data.plan.get("goals") or [] if all(k in g for k in core.LIFTS)],
                points,
                data.default_bodyweight("goals"),
            )
        ],
        goals_after=_sections(notes.get("goals_after")),
        tm_intro=_blocks(notes.get("tm_intro")),
        phases=phases,
        points=[
            PointOut(
                date=p.date,
                lift=p.lift,
                kg=p.kg,
                rpe=p.rpe,
                e1rm=p.e1rm,
                e1rm_rounded=round_to_step(p.e1rm),
                kind=p.kind,
            )
            for p in points
        ],
        start_date=dt.date.fromisoformat(meta["start_date"]),
        test_date=dt.date.fromisoformat(meta["test_date"]) if meta.get("test_date") else None,
        meet_date=data.meet,
        meet_name=meta.get("meet_name") or "Zawody",
    )


@router.put("/tm/{phase}", status_code=204)
def put_tm(phase: int, body: TmIn, db: Session = Depends(get_db)) -> Response:
    """TM fazy w całości (`setTm`). Wartość równa domyślnej nie zostaje zapisana ręcznie."""
    data = Loaded(db)
    if phase not in {w.phase for w in data.season}:
        raise HTTPException(404, "Nie ma takiej fazy w planie.")
    data.settings.tm = meet.with_tm(data.plan, data.settings.tm, phase, body.model_dump())
    if data.settings not in db:
        db.add(data.settings)
    db.commit()
    return Response(status_code=204)


class CalculatorOut(BaseModel):
    e1rm: float
    tm: float


@router.get("/calculator", response_model=CalculatorOut)
def get_calculator(
    kg: float = Query(gt=0, le=1000), reps: float = Query(gt=0, le=20), rpe: float = Query(gt=0)
) -> CalculatorOut:
    """Kalkulator e1RM: szacowany maks co 0,5 kg i TM w dół do 2,5 kg."""
    result = meet.calculator(kg, reps, rpe)
    if isinstance(result, str):
        raise HTTPException(422, result)
    return CalculatorOut(**result)


# ---------------------------------------------------------------- start


class AttemptRow(BaseModel):
    lift: str
    max: float
    from_singles: bool
    fallback_phase: int
    first: float
    second: float
    third: tuple[float, float]


class Ladder(BaseModel):
    lift: str
    steps: list[tuple[float, int]]  # (kg, powtórzenia)
    opener: float


class AttemptPlan(BaseModel):
    rows: list[AttemptRow]
    total_first: float
    total_second: float
    total_third: tuple[float, float]
    ladders: list[Ladder]


class ResultRow(BaseModel):
    label: str
    S: float | None
    B: float | None
    D: float | None
    total: float | None
    gl: float | None
    baseline: bool = False
    empty: bool = False  # jeszcze bez zaliczonych podejść


class StartCard(BaseModel):
    name: str
    date: dt.date
    week_index: int | None  # tydzień z arkuszem
    intro: list[NoteBlock]
    after_table: list[NoteBlock]
    after_ladder: list[NoteSection]
    attempts: AttemptPlan


class StartOut(BaseModel):
    test: StartCard | None
    meet: StartCard
    meet_default: bool  # data zakładana, jeszcze bez komunikatu
    meet_range: tuple[dt.date, dt.date] | None
    adjustment: str
    results: list[ResultRow]
    results_note: list[NoteBlock]


def _attempt_plan(data: Loaded, context: str) -> AttemptPlan:
    rows, ladders = [], []
    for lift in core.LIFTS:
        value, from_singles, phase = data.context_max(context, lift)
        plan = attempts_for(value, lift)
        rows.append(
            AttemptRow(
                lift=lift,
                max=round_to_step(value),
                from_singles=from_singles,
                fallback_phase=phase,
                first=plan["first"],
                second=plan["second"],
                third=plan["third"],
            )
        )
        ladders.append(
            Ladder(lift=lift, steps=meet.warmup_ladder(plan["first"], lift), opener=plan["first"])
        )
    return AttemptPlan(
        rows=rows,
        total_first=sum(r.first for r in rows),
        total_second=sum(r.second for r in rows),
        total_third=(sum(r.third[0] for r in rows), sum(r.third[1] for r in rows)),
        ladders=ladders,
    )


def _labeled_week(data: Loaded, label: str) -> int | None:
    return next((i for i, w in enumerate(data.season) if w.template.get("label") == label), None)


def _result(data: Loaded, label: str, week: int | None, last: bool, context: str) -> ResultRow:
    if week is None:
        return ResultRow(label=label, S=None, B=None, D=None, total=None, gl=None, empty=True)
    slot = data.season[week].sessions[-1 if last else 0]
    log = data.logs.get(slot.key) or {}
    r = meet.sheet_result(
        slot.day.get("exercises") or [],
        log.get("entries") or {},
        core.number(log.get("bodyweight")),
        data.default_bodyweight(context),
    )
    best = r["best"]
    return ResultRow(
        label=label,
        S=best["S"],
        B=best["B"],
        D=best["D"],
        total=r["total"],
        gl=r["gl"],
        empty=not any(best.values()),
    )


@router.get("/start", response_model=StartOut)
def get_start(db: Session = Depends(get_db)) -> StartOut:
    data = Loaded(db)
    notes = _notes(data).get("start") or {}
    meta = data.plan["meta"]
    meet_name = meta.get("meet_name") or "Zawody"
    test_week = _labeled_week(data, "TEST")
    meet_week = _labeled_week(data, "AMP")
    test = None
    if meta.get("test_date"):
        test = StartCard(
            name="Test",
            date=dt.date.fromisoformat(meta["test_date"]),
            week_index=test_week,
            intro=_blocks(notes.get("test_intro")),
            after_table=_blocks(notes.get("test_after")),
            after_ladder=[],
            attempts=_attempt_plan(data, "test"),
        )
    results = []
    baseline = next((g for g in data.plan.get("goals") or [] if g.get("baseline")), None)
    if baseline and all(k in baseline for k in core.LIFTS):
        row = meet.goal_rows([baseline], [], data.default_bodyweight("goals"))[0]
        results.append(ResultRow(**{**row, "baseline": True}))
    if test:
        results.append(
            _result(data, f"Test {test.date.day}.{test.date.month:02d}", test_week, False, "test")
        )
    results.append(_result(data, meet_name, meet_week, True, "meet"))
    rng = meta.get("meet_date_range")
    return StartOut(
        test=test,
        meet=StartCard(
            name=meet_name,
            date=data.meet,
            week_index=meet_week,
            intro=_blocks(notes.get("meet_intro")),
            after_table=[],
            after_ladder=_sections(notes.get("meet_after_ladder")),
            attempts=_attempt_plan(data, "meet"),
        ),
        meet_default=data.settings.meet_date is None,
        meet_range=(dt.date.fromisoformat(rng[0]), dt.date.fromisoformat(rng[1]))
        if isinstance(rng, list) and len(rng) == 2
        else None,
        adjustment=meet.describe_adjustment(data.season, data.settings.adj or {}, data.plan),
        results=results,
        results_note=_blocks(notes.get("results_note")),
    )


class MeetIn(BaseModel):
    date: dt.date
    today: dt.date  # data z telefonu: zmieniać można tylko tygodnie, które jeszcze nie minęły


@router.put("/meet", status_code=204)
def put_meet(body: MeetIn, db: Session = Depends(get_db)) -> Response:
    """Data zawodów i dopasowanie długości planu (`computeAdj`). Wymaga sieci."""
    data = Loaded(db)
    meta = data.plan["meta"]
    rng = meta.get("meet_date_range")
    if isinstance(rng, list) and len(rng) == 2:
        if not rng[0] <= body.date.isoformat() <= rng[1]:
            raise HTTPException(422, f"Data spoza zakresu planu ({rng[0]} – {rng[1]}).")
    rules = data.plan.get("meet_date_adjustment") or {}
    if not {"spring_weeks", "relative_days"} <= set(rules) or not meta.get("spring_block_start"):
        raise HTTPException(422, "Ten plan nie ma reguł dopasowania do daty zawodów.")
    result = meet.adjust_for_meet(
        [w["id"] for w in data.plan["weeks"]],
        dt.date.fromisoformat(meta["start_date"]),
        data.settings.adj or {},
        body.date,
        body.today,
        rules,
        dt.date.fromisoformat(meta["spring_block_start"]),
    )
    if isinstance(result, str):
        raise HTTPException(422, result)
    data.settings.adj = result
    default = meta.get("default_meet_date")
    data.settings.meet_date = None if body.date.isoformat() == default else body.date
    if data.settings not in db:
        db.add(data.settings)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- zasady


class RulesOut(BaseModel):
    sections: list[NoteSection]


@router.get("/rules", response_model=RulesOut)
def get_rules(db: Session = Depends(get_db)) -> RulesOut:
    return RulesOut(sections=_sections(_notes(Loaded(db)).get("rules")))
