"""Start, maksy i dopasowanie planu do daty zawodów (etap 4, część 2, 26.11.2026).

Przeniesione 1:1 z żywej wersji planu: `maxFor`, `attemptsFor`, `ladder`, `sheetResult`,
`thirdText`, `computeAdj`, `describeAdj`, `setTm`, `calcText`, `goalsCard`.
Czyste funkcje na danych; teksty dla użytkownika składa frontend albo API.
"""

import datetime as dt
from collections.abc import Mapping, Sequence

from app.core.season import LIFTS, LiftPoint, WeekSlot, best_e1rm, number, week_keys
from app.core.training import (
    attempts_for,
    e1rm,
    floor_to_step,
    gl_coefficient,
    js_round,
    round_to_step,
    third_from_second,
    tm_for,
)

DEFAULT_BODYWEIGHT = 74.0  # gdy plan nie podaje masy ciała do punktów GL
MAX_SHIFT_WEEKS = 4  # dalej od planowanej daty plan wymaga przebudowy, nie dopasowania


# ---------------------------------------------------------------- maks do podejść


def context_max(
    points: Sequence[LiftPoint], context_weeks: Sequence[str], fallback_tm: float, lift: str
) -> tuple[float, bool]:
    """Maks do podejść (`maxFor`): najlepszy e1RM z singli (RPE ≥ 8) z tygodni kontekstu.

    Zwraca (wartość, czy z singli). Bez singli: TM fazy zastępczej z planu.
    """
    ids = set(context_weeks)
    best = best_e1rm(
        points, lift, lambda p: p.template_id in ids and p.rpe >= 8 and p.kind == "single"
    )
    return (best, True) if best else (fallback_tm, False)


def warmup_ladder(opener: float, lift: str) -> list[tuple[float, int]]:
    """Rozgrzewka pod otwarcie (`ladder`): (kg, powtórzenia), każdy krok cięższy."""
    steps = [
        (20.0, 5 if lift == "D" else 8),
        (round_to_step(opener * 0.4), 5),
        (round_to_step(opener * 0.6), 3),
        (round_to_step(opener * 0.75), 2),
        (round_to_step(opener * 0.85), 1),
        (round_to_step(opener * 0.92), 1),
    ]
    out: list[tuple[float, int]] = []
    for kg, reps in steps:
        if not out or kg > out[-1][0]:
            out.append((float(kg), reps))
    return out


def sheet_result(
    exercises: Sequence[Mapping],
    entries: Mapping[int, Mapping],
    bodyweight: float | None,
    default_bodyweight: float,
) -> dict:
    """Najlepsze zaliczone podejścia, suma i punkty GL (`sheetResult`)."""
    best: dict[str, float | None] = dict.fromkeys(LIFTS)
    for i, ex in enumerate(exercises):
        e = entries.get(i) or {}
        kg = number(e.get("kg"))
        lift = ex.get("lift")
        if ex.get("kind") == "att" and e.get("ok") == "y" and kg and lift in best:
            if best[lift] is None or kg > best[lift]:
                best[lift] = kg
    values = [best[lift] for lift in LIFTS]
    total = sum(v for v in values if v) if all(values) else None
    bw = bodyweight or default_bodyweight
    return {
        "best": best,
        "total": total,
        "bodyweight": bw,
        "gl": total * gl_coefficient(bw) if total else None,
    }


def third_hint(second: Mapping | None, lift: str) -> dict:
    """Podpowiedź trzeciego podejścia po drugim (`thirdText`), bez tekstu.

    kind: failed (spalone), rules (jeszcze bez zaliczonego drugiego), need_rpe,
    limit (drugie było na granicy), next (ciężar trzeciego).
    """
    e = second or {}
    kg, rpe = number(e.get("kg")), number(e.get("rpe"))
    if e.get("ok") == "n":
        return {"kind": "failed"}
    if e.get("ok") != "y" or not kg:
        return {"kind": "rules"}
    hint = third_from_second(kg, rpe or 0, lift)
    if hint is None:
        return {"kind": "need_rpe"}
    if hint["inc"] == 0:
        return {"kind": "limit", "kg": kg}
    return {"kind": "next", "kg": hint["kg"], "rpe": rpe}


# ---------------------------------------------------------------- maksy treningowe


def tm_default(plan: Mapping, overrides: Mapping | None, phase: int, lift: str) -> float:
    """TM bez ręcznego wpisu w tej fazie: plan dla fazy 1, inaczej poprzednia faza + przyrost."""
    tm = plan["training_max"]
    if phase <= 1:
        return float(tm["phase_1"][lift])
    increments = tm.get("default_increment_by_phase") or {}
    previous = tm_for(phase - 1, lift, tm["phase_1"], increments, overrides)
    return previous + increments[str(phase)][lift]


def with_tm(
    plan: Mapping, overrides: Mapping | None, phase: int, values: Mapping[str, float | None]
) -> dict:
    """Nowe ręczne TM po wpisie w fazie (`setTm`). Brak albo wartość domyślna usuwa wpis."""
    out = {str(k): dict(v) for k, v in (overrides or {}).items() if isinstance(v, Mapping)}
    current = out.get(str(phase), {})
    for lift, value in values.items():
        if lift not in LIFTS:
            continue
        default = tm_default(plan, out, phase, lift)
        if value is None or value <= 0 or abs(value - default) < 1e-9:
            current.pop(lift, None)
        else:
            current[lift] = float(value)
    if current:
        out[str(phase)] = current
    else:
        out.pop(str(phase), None)
    return out


def calculator(kg: float, reps: float, rpe: float) -> dict | str:
    """Kalkulator e1RM (`calcText`): e1RM co 0,5 kg i TM w dół do 2,5 kg albo błąd."""
    if reps < 1 or reps > 6 or rpe < 6 or rpe > 10:
        return "Powtórzenia 1–6, RPE 6–10."
    value = e1rm(kg, js_round(reps), js_round(rpe * 2) / 2)
    if not value:
        return "Poza tabelą RPE."
    return {"e1rm": js_round(value * 2) / 2, "tm": floor_to_step(value)}


def goal_rows(
    goals: Sequence[Mapping], points: Sequence[LiftPoint], default_bodyweight: float
) -> list[dict]:
    """Tabela celów z wierszem „Teraz” z singli (`goalsCard`): sumy i punkty GL."""
    rows = [dict(g) for g in goals]
    now = {lift: best_e1rm(points, lift, lambda _p: True) for lift in LIFTS}
    if all(now.values()):
        rows.insert(
            1,
            {"label": "Teraz (z singli)", "baseline": True}
            | {lift: floor_to_step(v) for lift, v in now.items() if v},
        )
    out = []
    for g in rows:
        total = sum(float(g[lift]) for lift in LIFTS)
        bw = g.get("bodyweight_kg") or default_bodyweight
        out.append(
            {
                "label": g["label"],
                **{lift: float(g[lift]) for lift in LIFTS},
                "total": total,
                "gl": total * gl_coefficient(bw),
                "baseline": bool(g.get("baseline")),
            }
        )
    return out


# ---------------------------------------------------------------- data zawodów


def mondays(template_ids: Sequence[str], start: dt.date, adj: Mapping) -> dict[str, dt.date]:
    return {k: start + dt.timedelta(days=7 * i) for i, k in enumerate(week_keys(template_ids, adj))}


def weeks_needed(meet: dt.date, spring_start: dt.date, relative_days: int) -> int:
    """Ile zwykłych tygodni mieści się od początku wiosny do tygodni liczonych od startu."""
    return (((meet - dt.timedelta(days=relative_days)) - spring_start).days - 6) // 7 + 1


def adjust_for_meet(
    template_ids: Sequence[str],
    start: dt.date,
    adj: Mapping,
    meet: dt.date,
    today: dt.date,
    rules: Mapping,
    spring_start: dt.date,
) -> dict | str:
    """Dopasowanie długości planu do daty zawodów (`computeAdj`).

    Najpierw cofa wcześniejsze zmiany w tygodniach, które jeszcze nie minęły, potem
    dodaje powtórkę albo usuwa tydzień z `prefer_weeks`. Zwraca nowe `adj` albo błąd.
    """
    prefer = list(rules.get("prefer_weeks") or [])
    base = int(rules["spring_weeks"])
    relative = int(rules["relative_days"])
    ins = [k for k in adj.get("ins") or []]
    rem = [k for k in adj.get("rem") or []]
    diff = weeks_needed(meet, spring_start, relative) - (base + len(ins) - len(rem))
    if abs(diff) > MAX_SHIFT_WEEKS:
        return "Ta data jest za daleko od planowanej. Końcówka planu wymaga przebudowy."

    def mons(i: list[str], r: list[str]) -> dict[str, dt.date]:
        return mondays(template_ids, start, {"ins": i, "rem": r})

    def drop_last(items: list[str], key: str) -> None:
        del items[len(items) - 1 - items[::-1].index(key)]

    while diff < 0:
        m = mons(ins, rem)
        k = next((x for x in reversed(ins) if (d := m.get(x + "b")) and d > today), None)
        if k is None:
            break
        drop_last(ins, k)
        diff += 1
    while diff > 0:
        k = next(
            (
                x
                for x in reversed(rem)
                if (d := mons(ins, [y for y in rem if y != x]).get(x)) and d > today
            ),
            None,
        )
        if k is None:
            break
        drop_last(rem, k)
        diff -= 1
    while diff > 0:
        m = mons(ins, rem)
        k = next(
            (
                x
                for x in prefer
                if x not in ins
                and x not in rem
                and (d := m.get(x))
                and d + dt.timedelta(days=7) > today
            ),
            None,
        )
        if k is None:
            return "Za późno na automatyczne wydłużenie planu."
        ins.append(k)
        diff -= 1
    while diff < 0:
        m = mons(ins, rem)
        k = next(
            (x for x in prefer if x not in rem and x not in ins and (d := m.get(x)) and d > today),
            None,
        )
        if k is None:
            return "Za późno na automatyczne skrócenie planu."
        rem.append(k)
        diff += 1
    return {"ins": ins, "rem": rem}


def describe_adjustment(season: Sequence[WeekSlot], adj: Mapping, plan: Mapping) -> str:
    """Opis zmian długości planu (`describeAdj`). Usuniętego tygodnia nie ma w sezonie,
    więc jego blok bierzemy z planu."""
    blocks = plan.get("blocks") or {}
    templates = {w["id"]: w for w in plan["weeks"]}

    def block_name(block: str) -> str:
        return (blocks.get(block) or {}).get("name") or block

    parts = []
    for k in adj.get("ins") or []:
        week = next((w for w in season if w.key == k + "b"), None)
        if week:
            name = block_name(week.template["block"])
            parts.append(f"dodatkowy tydzień {week.n} (powtórka tygodnia {week.repeat_of}, {name})")
    for k in adj.get("rem") or []:
        if k in templates:
            parts.append(f"bez jednego tygodnia bloku {block_name(templates[k]['block'])}")
    if not parts:
        return "Plan ułożony bez zmian długości."
    return "Dopasowanie do daty: " + "; ".join(parts) + "."


__all__ = [
    "attempts_for",
    "adjust_for_meet",
    "calculator",
    "context_max",
    "describe_adjustment",
    "goal_rows",
    "sheet_result",
    "third_hint",
    "tm_default",
    "warmup_ladder",
    "with_tm",
]
