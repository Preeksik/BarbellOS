"""Start, maksy i data zawodów (app/core/meet.py).

Zgodność z oryginalnym JavaScriptem sprawdzono przy przenoszeniu na prawdziwym planie
i dzienniku (26.11.2026, trzy daty „dziś”, osiem dat zawodów, zero różnic).
"""

import datetime as dt

import pytest

from app.core import meet as m
from app.core import season as s
from tests.training_plan import make_plan


def point(lift: str, e1: float, template: str = "t01", kind: str = "single", rpe: float = 8):
    return s.LiftPoint(dt.date(2026, 11, 2), lift, e1, rpe, e1, 1, template, kind)


def test_context_max_uses_heavy_singles_from_context_weeks():
    points = [
        point("S", 180, "t06"),
        point("S", 190, "t06", rpe=7.5),  # za lekki single (RPE < 8)
        point("S", 200, "t02"),  # spoza tygodni kontekstu
        point("S", 185, "t07", kind="att"),  # podejście, nie single
    ]
    assert m.context_max(points, ["t06", "t07"], 170, "S") == (180, True)
    assert m.context_max(points, ["t06"], 170, "B") == (170, False)


def test_warmup_ladder():
    assert m.warmup_ladder(157.5, "S") == [
        (20, 8),
        (62.5, 5),
        (95, 3),
        (117.5, 2),
        (135, 1),
        (145, 1),
    ]
    # Martwy: 5 powtórzeń na sztandze; kroki nie mogą się powtarzać.
    assert m.warmup_ladder(40, "D") == [(20, 5), (25, 3), (30, 2), (35, 1), (37.5, 1)]


def test_sheet_result_and_third_hint():
    exercises = [{"kind": "att", "lift": lift, "attempt": a} for lift in "SBD" for a in (1, 2, 3)]
    entries = {
        0: {"kg": 165, "ok": "y"},
        1: {"kg": 172.5, "ok": "y", "rpe": 8},
        2: {"kg": 180, "ok": "n"},
        3: {"kg": 120, "ok": "y"},
        6: {"kg": 200, "ok": "y"},
    }
    r = m.sheet_result(exercises, entries, None, 75)
    assert r["best"] == {"S": 172.5, "B": 120, "D": 200}
    assert r["total"] == 492.5 and r["bodyweight"] == 75
    assert r["gl"] == pytest.approx(
        492.5 * 100 / (1199.72839 - 1025.18162 * 2.718281828 ** (-0.00921 * 75)), rel=1e-6
    )
    assert m.sheet_result(exercises, {0: {"kg": 165, "ok": "y"}}, 76, 75)["total"] is None

    assert m.third_hint({"kg": 172.5, "ok": "y", "rpe": 8}, "S") == {
        "kind": "next",
        "kg": 180,
        "rpe": 8,
    }
    assert m.third_hint({"kg": 125, "ok": "y", "rpe": 9.5}, "B") == {"kind": "limit", "kg": 125}
    assert m.third_hint({"kg": 125, "ok": "y"}, "B") == {"kind": "need_rpe"}
    assert m.third_hint({"kg": 125, "ok": "n"}, "B") == {"kind": "failed"}
    assert m.third_hint(None, "D") == {"kind": "rules"}


def test_with_tm_keeps_only_manual_values():
    plan = make_plan()  # faza 1: S 160; faza 2: +5
    assert m.tm_default(plan, {}, 2, "S") == 165
    assert m.with_tm(plan, {}, 2, {"S": 170, "B": None, "D": 205}) == {"2": {"S": 170}}
    # Domyślna fazy 2 zależy od ręcznej fazy 1.
    overrides = {"1": {"S": 150}}
    assert m.tm_default(plan, overrides, 2, "S") == 155
    assert m.with_tm(plan, {"2": {"S": 170}}, 2, {"S": None, "B": None, "D": None}) == {}


def test_calculator():
    assert m.calculator(150, 1, 8) == {"e1rm": 162.5, "tm": 162.5}
    assert m.calculator(100, 5, 8.5) == {"e1rm": 121.5, "tm": 120}  # 82,4% z tabeli
    assert m.calculator(100, 7, 8) == "Powtórzenia 1–6, RPE 6–10."


def test_goal_rows_with_current_row():
    goals = [
        {
            "label": "Zeszły rok",
            "S": 150,
            "B": 105,
            "D": 190,
            "bodyweight_kg": 73.6,
            "baseline": True,
        },
        {"label": "Realnie", "S": 187.5, "B": 135, "D": 227.5},
    ]
    rows = m.goal_rows(goals, [point("S", 173.5), point("B", 131), point("D", 212.4)], 74)
    assert [r["label"] for r in rows] == ["Zeszły rok", "Teraz (z singli)", "Realnie"]
    assert (rows[1]["S"], rows[1]["B"], rows[1]["D"], rows[1]["total"]) == (172.5, 130, 210, 512.5)
    assert rows[0]["gl"] == pytest.approx(65.51, abs=0.01)  # jak w starym pliku
    # Bez singla w którymś boju nie ma wiersza „Teraz”.
    assert len(m.goal_rows(goals, [point("S", 173.5)], 74)) == 2


RULES = {"prefer_weeks": ["t02", "t01"], "spring_weeks": 2, "relative_days": 3}
IDS = ["t01", "t02", "t03"]
START = dt.date(2026, 10, 26)
SPRING = dt.date(2026, 10, 26)


def test_weeks_needed_and_adjust_for_meet():
    # Zawody 29.11: od 26.10 do 26.11 mieszczą się 5 tygodnie, a plan ma 2 zwykłe.
    assert m.weeks_needed(dt.date(2026, 11, 15), SPRING, 3) == 2
    today = dt.date(2026, 10, 20)
    longer = m.adjust_for_meet(IDS, START, {}, dt.date(2026, 11, 29), today, RULES, SPRING)
    assert longer == {"ins": ["t02", "t01"], "rem": []}
    shorter = m.adjust_for_meet(IDS, START, {}, dt.date(2026, 11, 8), today, RULES, SPRING)
    assert shorter == {"ins": [], "rem": ["t02"]}
    # Powrót do pierwotnej daty cofa dodane tygodnie.
    back = m.adjust_for_meet(IDS, START, longer, dt.date(2026, 11, 15), today, RULES, SPRING)
    assert back == {"ins": [], "rem": []}
    assert isinstance(
        m.adjust_for_meet(IDS, START, {}, dt.date(2027, 3, 1), today, RULES, SPRING), str
    )
    # Tygodnie, które już minęły, nie dają się zmienić.
    late = dt.date(2026, 11, 20)
    assert m.adjust_for_meet(IDS, START, {}, dt.date(2026, 11, 29), late, RULES, SPRING) == (
        "Za późno na automatyczne wydłużenie planu."
    )


def test_describe_adjustment():
    plan = make_plan()
    adj = {"ins": ["t01"], "rem": ["t02"]}
    season = s.build_season(plan, dt.date(2026, 11, 29), adj)
    assert m.describe_adjustment(season, adj, plan) == (
        "Dopasowanie do daty: dodatkowy tydzień 2 (powtórka tygodnia 1, Akumulacja I); "
        "bez jednego tygodnia bloku Intensyfikacja I."
    )
    assert m.describe_adjustment(season, {}, plan) == "Plan ułożony bez zmian długości."
