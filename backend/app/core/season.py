"""Kalendarz sezonu i dziennik treningowy (etap 4, 25.11.2026).

Przeniesione 1:1 z żywej wersji planu (artefakt z 22.11.2026): `buildSeq`, `sessStatus`,
`points`, `sugFor`, `lastFor`, `nextInOrder`, `platesFor`. Dziennik ma postać:

    {klucz sesji: {"entries": {indeks ćwiczenia: {"kg", "reps", "rpe", "done", "ok"}},
                   "gym": str | None, "at": datetime | None}}

Jeden wpis odpowiada jednemu ćwiczeniu sesji (np. „4 × 4"), tak jak w starym pliku.
"""

import datetime as dt
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.core.training import STEP_KG, e1rm, floor_to_step, js_round, load_for, tm_for

PLATES_KG = (25, 20, 15, 10, 5, 2.5, 1.25)
BAR_KG = 20
COLLARS_KG = 5  # para zacisków zawodniczych
FRESH_SESSION = dt.timedelta(hours=8)  # sesja zapisana niedawno nadal jest „dzisiejsza"
NEXT_SESSION_WINDOW_DAYS = 6
LIFTS = ("S", "B", "D")
SESSION_KEY_MAX = 16  # długość kolumny session_log.session_key

Logs = Mapping[str, Mapping]


@dataclass(frozen=True)
class SessionSlot:
    """Jedna sesja w kalendarzu: szablon dnia z planu i jego data."""

    key: str  # np. "t03-D2", powtórzony tydzień: "t18b-D1"
    week_index: int
    day_index: int
    date: dt.date
    day: Mapping  # dzień z planu: code, title, minutes, exercises, …


@dataclass(frozen=True)
class WeekSlot:
    key: str  # id szablonu, z sufiksem „b" dla powtórki
    template: Mapping
    n: int  # numer tygodnia od 1
    repeat_of: int | None  # numer tygodnia, który ten powtarza
    start: dt.date
    end: dt.date
    phase: int
    sessions: tuple[SessionSlot, ...]


def week_keys(template_ids: Sequence[str], adj: Mapping | None) -> list[str]:
    """Kolejność tygodni po dopasowaniu do daty zawodów (`keysFor`)."""
    adj = adj or {}
    removed = set(adj.get("rem") or [])
    keys = [k for k in template_ids if k not in removed]
    for k in adj.get("ins") or []:
        if k in keys:
            keys.insert(keys.index(k) + 1, k + "b")
    return keys


def build_season(plan: Mapping, meet_date: dt.date, adj: Mapping | None) -> list[WeekSlot]:
    """Tygodnie sezonu z datami (`buildSeq`). Tydzień n zaczyna się start + 7·(n−1),
    a dni z `days_before_meet` liczą się wstecz od daty zawodów."""
    templates = {w["id"]: w for w in plan["weeks"]}
    start = dt.date.fromisoformat(plan["meta"]["start_date"])
    keys = week_keys([w["id"] for w in plan["weeks"]], adj)
    season = []
    for i, key in enumerate(keys):
        template = templates[key.removesuffix("b")]
        monday = start + dt.timedelta(days=7 * i)
        relative = any(d.get("days_before_meet") is not None for d in template["days"])
        sessions = tuple(
            SessionSlot(
                key=f"{key}-{d['code']}",
                week_index=i,
                day_index=j,
                date=(
                    meet_date - dt.timedelta(days=d["days_before_meet"])
                    if d.get("days_before_meet") is not None
                    else monday + dt.timedelta(days=d.get("day_offset") or 0)
                ),
                day=d,
            )
            for j, d in enumerate(template["days"])
        )
        repeat = key.endswith("b")
        season.append(
            WeekSlot(
                key=key,
                template=template,
                n=i + 1,
                repeat_of=keys.index(key[:-1]) + 1 if repeat else None,
                start=sessions[0].date if relative else monday,
                end=sessions[-1].date if relative else monday + dt.timedelta(days=6),
                phase=template["phase"],
                sessions=sessions,
            )
        )
    return season


def all_sessions(season: Sequence[WeekSlot]) -> list[SessionSlot]:
    return [s for w in season for s in w.sessions]


def plan_errors(plan: object) -> list[str]:
    """Czego brakuje w pliku planu, zanim trafi do bazy (komunikaty po polsku)."""
    if not isinstance(plan, Mapping):
        return ["Plik planu nie jest obiektem JSON."]
    errors = []
    meta = plan.get("meta")
    if not isinstance(meta, Mapping) or not _is_iso_date(meta.get("start_date")):
        errors.append("Brak daty startu planu (meta.start_date).")
    tm = plan.get("training_max")
    if not isinstance(tm, Mapping) or not all(
        isinstance((tm.get("phase_1") or {}).get(lift), int | float) for lift in LIFTS
    ):
        errors.append("Brak maksów treningowych fazy 1 (training_max.phase_1).")
    weeks = plan.get("weeks")
    if not isinstance(weeks, list) or not weeks:
        return [*errors, "Plan nie ma tygodni (weeks)."]
    for week in weeks:
        if not isinstance(week, Mapping) or not isinstance(week.get("id"), str):
            errors.append("Tydzień bez identyfikatora.")
            continue
        days = week.get("days")
        if not isinstance(days, list) or not days:
            errors.append(f"Tydzień {week['id']} nie ma dni.")
            continue
        for day in days:
            if not isinstance(day, Mapping) or not isinstance(day.get("code"), str):
                errors.append(f"Tydzień {week['id']}: dzień bez kodu.")
            elif len(f"{week['id']}b-{day['code']}") > SESSION_KEY_MAX:
                errors.append(f"Tydzień {week['id']}: za długi kod dnia {day['code']}.")
            elif not isinstance(day.get("exercises"), list):
                errors.append(f"Tydzień {week['id']}, dzień {day['code']}: brak ćwiczeń.")
    return errors[:10]


def _is_iso_date(value: object) -> bool:
    try:
        dt.date.fromisoformat(str(value))
    except ValueError:
        return False
    return True


def tm_value(plan: Mapping, overrides: Mapping | None, phase: int, lift: str) -> float:
    """TM boju w fazie: wpisany ręcznie albo z planu (poprzednia faza + przyrost)."""
    tm = plan["training_max"]
    return tm_for(phase, lift, tm["phase_1"], tm.get("default_increment_by_phase") or {}, overrides)


def plates_for(total_kg: float, collars: bool = False, largest: float = 25) -> list[float] | None:
    """Talerze na jedną stronę sztangi (od największego). Za mało na sztangę: None.

    `largest`: największy talerz na siłowni (np. 20 kg, gdy nie ma 25 kg).
    """
    side = (total_kg - BAR_KG - (COLLARS_KG if collars else 0)) / 2
    if side < -1e-9:
        return None
    plates = []
    for plate in (p for p in PLATES_KG if p <= largest):
        while side >= plate - 1e-9:
            plates.append(plate)
            side -= plate
    return plates


def planned_load(exercise: Mapping, tm: float) -> float | None:
    """Ciężar z planu: stały (`fixed_kg`, np. tygodnie sprzed zmiany maksów) albo z TM."""
    if exercise.get("fixed_kg") is not None:
        return float(exercise["fixed_kg"])
    return load_for(exercise, tm)


def entry_e1rm(exercise: Mapping, entry: Mapping) -> float | None:
    """e1RM z wpisu (`exE1`): single i serie bojów, RPE ponad 10 liczone jak 10."""
    kg, rpe = number(entry.get("kg")), number(entry.get("rpe"))
    if not kg or not rpe:
        return None
    if exercise.get("kind") == "single":
        return e1rm(kg, 1, min(10, rpe))
    if exercise.get("kind") == "sets" and exercise.get("tier") == "main":
        reps = number(entry.get("reps"))
        return e1rm(kg, js_round(reps), min(10, rpe)) if reps else None
    return None


def session_status(exercises: Sequence[Mapping], entries: Mapping[int, Mapping]) -> str:
    """'none' | 'part' | 'done' (`sessStatus`): zrobione to odhaczone albo z oceną podejścia."""
    done = sum(
        1 for i in range(len(exercises)) if (e := entries.get(i)) and (e.get("done") or e.get("ok"))
    )
    if not done:
        return "part" if entries else "none"
    return "done" if done >= len(exercises) else "part"


def _entries(logs: Logs, key: str) -> Mapping[int, Mapping]:
    return (logs.get(key) or {}).get("entries") or {}


@dataclass(frozen=True)
class LiftPoint:
    """Wynik z dziennika do wykresu i sugestii TM (`points`)."""

    date: dt.date
    lift: str
    kg: float
    rpe: float
    e1rm: float
    phase: int
    template_id: str
    kind: str  # 'single' | 'att'


def lift_points(season: Sequence[WeekSlot], logs: Logs) -> list[LiftPoint]:
    points = []
    for week in season:
        for slot in week.sessions:
            entries = _entries(logs, slot.key)
            for i, ex in enumerate(slot.day["exercises"]):
                e = entries.get(i)
                kg = number(e.get("kg")) if e else None
                if not kg or ex.get("tier") != "main" or not ex.get("lift"):
                    continue
                if ex.get("kind") == "single":
                    rpe = number(e.get("rpe"))
                    value = e1rm(kg, 1, min(10, rpe)) if rpe and rpe >= 6 else None
                    kind = "single"
                elif ex.get("kind") == "att" and e.get("ok") == "y":
                    rpe = min(10, max(9, number(e.get("rpe")) or 10))
                    value = e1rm(kg, 1, rpe)
                    kind = "att"
                else:
                    continue
                if value and rpe:
                    point = LiftPoint(
                        slot.date, ex["lift"], kg, rpe, value, week.phase, week.template["id"], kind
                    )
                    points.append(point)
    points.sort(key=lambda p: p.date)
    return points


def best_e1rm(
    points: Iterable[LiftPoint], lift: str, accept: Callable[[LiftPoint], bool]
) -> float | None:
    values = [p.e1rm for p in points if p.lift == lift and accept(p)]
    return max(values) if values else None


def suggest_tm(points: Sequence[LiftPoint], phase: int, lift: str) -> float | None:
    """Nowy TM z poprzedniej fazy: zaliczone podejścia, a bez nich single (RPE ≥ 7),
    w dół do 2,5 kg."""
    if phase <= 1:
        return None
    attempt = best_e1rm(points, lift, lambda p: p.phase == phase - 1 and p.kind == "att")
    if attempt:
        return floor_to_step(attempt)
    single = best_e1rm(points, lift, lambda p: p.phase == phase - 1 and p.rpe >= 7)
    return floor_to_step(single) if single else None


def tm_suggestion(
    points: Sequence[LiftPoint], phase: int, lift: str, current: float
) -> float | None:
    """Sugestia do pokazania (`sugFor`): wyższa o co najmniej 2,5 kg, a po podejściach
    także niższa (wynik z pomostu jest pewniejszy niż projekcja)."""
    value = suggest_tm(points, phase, lift)
    if value is None:
        return None
    attempts = any(p.phase == phase - 1 and p.lift == lift and p.kind == "att" for p in points)
    if value - current >= STEP_KG or (attempts and abs(value - current) >= STEP_KG):
        return value
    return None


def normalize_gym(name: str | None) -> str:
    return " ".join(str(name or "").split()).lower()


def known_gyms(season: Sequence[WeekSlot], logs: Logs) -> list[str]:
    """Siłownie z dziennika, od ostatnio odwiedzonej, bez powtórzeń."""
    seen, out = set(), []
    for slot in sorted(all_sessions(season), key=lambda s: s.date, reverse=True):
        gym = (logs.get(slot.key) or {}).get("gym")
        if (n := normalize_gym(gym)) and n not in seen:
            seen.add(n)
            out.append(str(gym).strip())
    return out


def last_result(
    season: Sequence[WeekSlot], logs: Logs, name: str, gym: str | None, current: SessionSlot
) -> dict | None:
    """Ostatni wpis ćwiczenia przed tą sesją (`lastFor`): najpierw z tej samej siłowni."""
    wanted = normalize_gym(gym)
    best = latest = None
    for slot in all_sessions(season):
        if slot.key == current.key or slot.date > current.date:
            continue
        log = logs.get(slot.key) or {}
        entries = log.get("entries") or {}
        for i, ex in enumerate(slot.day["exercises"]):
            e = entries.get(i)
            kg = number(e.get("kg")) if e and ex.get("name") == name else None
            if kg is None:
                continue
            at = log.get("at")
            result = {
                "kg": kg,
                "reps": number(e.get("reps")),
                "rpe": number(e.get("rpe")),
                "date": slot.date,
                "shown": at.date() if isinstance(at, dt.datetime) else slot.date,
                "gym": str(log.get("gym") or "").strip(),
            }
            if latest is None or result["date"] > latest["date"]:
                latest = result
            if wanted and normalize_gym(result["gym"]) == wanted:
                if best is None or result["date"] > best["date"]:
                    best = result
    return best or latest


def locate_today(season: Sequence[WeekSlot], today: dt.date) -> tuple[int, int, bool]:
    """(tydzień, dzień, czy to dzisiejsza sesja): dzisiejsza albo najbliższa następna."""
    upcoming = None
    for week_index, week in enumerate(season):
        for day_index, slot in enumerate(week.sessions):
            if slot.date == today:
                return week_index, day_index, True
            if slot.date > today and upcoming is None:
                upcoming = (week_index, day_index, False)
    if upcoming:
        return upcoming
    last = len(season) - 1
    return last, len(season[last].sessions) - 1, False


def next_in_order(
    season: Sequence[WeekSlot], logs: Logs, today: dt.date, now: dt.datetime
) -> tuple[int, int] | None:
    """Sesja po ostatniej zapisanej (`nextInOrder`), bo treningi bywają przesunięte
    względem kalendarza. Zapisana w ciągu 8 godzin zostaje na ekranie."""
    flat = all_sessions(season)
    last = -1
    for i, slot in enumerate(flat):
        if session_status(slot.day["exercises"], _entries(logs, slot.key)) != "none":
            last = i
    if last < 0:
        return None
    at = (logs.get(flat[last].key) or {}).get("at")
    fresh = isinstance(at, dt.datetime) and abs(now - at) < FRESH_SESSION
    nxt = flat[last if fresh else min(last + 1, len(flat) - 1)]
    if abs((nxt.date - today).days) <= NEXT_SESSION_WINDOW_DAYS:
        return nxt.week_index, nxt.day_index
    return None


def auto_locate(
    season: Sequence[WeekSlot], logs: Logs, today: dt.date, now: dt.datetime
) -> tuple[int, int, bool]:
    """Sesja do pokazania po otwarciu: (tydzień, dzień, czy dziś wolne)."""
    found = next_in_order(season, logs, today, now)
    if found:
        return found[0], found[1], False
    week, day, exact = locate_today(season, today)
    return week, day, not exact


def current_week(season: Sequence[WeekSlot], today: dt.date) -> int | None:
    """Indeks tygodnia, w którym jest dzisiejsza data (`currentIdx`)."""
    for i, week in enumerate(season):
        if week.start <= today <= week.end:
            return i
    return None


def number(value: object) -> float | None:
    """Liczba z wpisu: liczba albo tekst z przecinkiem; reszta to brak (`num`)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value) if math.isfinite(value) else None
    try:
        parsed = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None
