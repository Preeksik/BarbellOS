"""Kalendarz sezonu i dziennik (app/core/season.py) na sztucznym planie.

Zgodność z oryginalnym JavaScriptem planu sprawdzono przy przenoszeniu na prawdziwym
planie i dzienniku (25.11.2026, cztery scenariusze, zero różnic). Te testy pilnują
tych samych reguł na danych, które mogą być w publicznym repo.
"""

import datetime as dt

import pytest

from app.core import season as s
from tests.training_plan import make_plan

MEET = dt.date(2026, 11, 29)
UTC = dt.UTC


def log(entries: dict, at: dt.datetime | None = None, gym: str | None = None) -> dict:
    return {"entries": entries, "at": at, "gym": gym}


def test_build_season_dates_and_keys():
    season = s.build_season(make_plan(), MEET, None)
    assert [w.key for w in season] == ["t01", "t02", "t03"]
    assert [x.key for x in season[0].sessions] == ["t01-D1", "t01-D2"]
    assert season[0].sessions[1].date == dt.date(2026, 10, 28)  # poniedziałek + 2
    assert (season[0].start, season[0].end) == (dt.date(2026, 10, 26), dt.date(2026, 11, 1))
    # Tydzień startowy liczy się od daty zawodów, a jego granice to pierwszy i ostatni dzień.
    assert [x.date for x in season[2].sessions] == [dt.date(2026, 11, 26), MEET]
    assert (season[2].start, season[2].end) == (dt.date(2026, 11, 26), MEET)


def test_week_keys_repeat_and_remove():
    assert s.week_keys(["t01", "t02", "t03"], {"ins": ["t01"], "rem": ["t02"]}) == [
        "t01",
        "t01b",
        "t03",
    ]
    season = s.build_season(make_plan(), MEET, {"ins": ["t01"], "rem": []})
    assert season[1].key == "t01b" and season[1].repeat_of == 1
    assert season[1].sessions[0].key == "t01b-D1"
    assert season[2].start == dt.date(2026, 11, 9)  # dalsze tygodnie przesunięte o tydzień


def test_plates_for():
    assert s.plates_for(195) == [25, 25, 25, 10, 2.5]
    assert s.plates_for(20) == []
    assert s.plates_for(17.5) is None
    assert s.plates_for(102.5, collars=True) == [25, 10, 2.5, 1.25]
    # Siłownia bez talerzy 25 kg: te same kilogramy z dwudziestek.
    assert s.plates_for(195, largest=20) == [20, 20, 20, 20, 5, 2.5]


def test_planned_load_prefers_fixed_kg():
    single, sets = make_plan()["weeks"][0]["days"][0]["exercises"][:2]
    assert s.planned_load(single, 160) == 145  # stały ciężar sprzed zmiany maksów
    assert s.planned_load(sets, 160) == 125  # 160 · 78% = 124,8 → 125


def test_entry_e1rm():
    single, sets, acc = make_plan()["weeks"][0]["days"][0]["exercises"]
    assert s.entry_e1rm(single, {"kg": 195, "rpe": 8}) == pytest.approx(195 / 0.922)
    assert s.entry_e1rm(single, {"kg": 195, "rpe": 11}) == 195  # RPE ponad 10 jak 10
    assert s.entry_e1rm(sets, {"kg": 125, "reps": 4, "rpe": 8}) == pytest.approx(125 / 0.837)
    assert s.entry_e1rm(sets, {"kg": 125, "rpe": 8}) is None  # bez powtórzeń
    assert s.entry_e1rm(acc, {"kg": 30, "reps": 15, "rpe": 8}) is None


def test_session_status():
    exercises = [{}, {}, {}]
    assert s.session_status(exercises, {}) == "none"
    assert s.session_status(exercises, {0: {"kg": 100}}) == "part"
    assert s.session_status(exercises, {0: {"done": True}, 1: {"ok": "y"}}) == "part"
    done = {0: {"done": True}, 1: {"ok": "n"}, 2: {"done": True}}
    assert s.session_status(exercises, done) == "done"


def test_points_and_tm_suggestion():
    plan = make_plan()
    season = s.build_season(plan, MEET, None)
    logs = {
        "t01-D1": log({0: {"kg": 160, "rpe": 8}, 1: {"kg": 130, "reps": 4, "rpe": 8}}),
        "t03-AMP": log({0: {"kg": 170, "ok": "y"}, 1: {"kg": 180, "ok": "n"}}),
    }
    points = s.lift_points(season, logs)
    # Serie nie dają punktów, single i zaliczone podejścia tak (podejście bez RPE = 10).
    assert [(p.kind, p.kg, p.rpe) for p in points] == [("single", 160, 8), ("att", 170, 10)]
    # Faza 2: single z fazy 1 (160 / 0,922 = 173,5 → 172,5).
    assert s.suggest_tm(points, 2, "S") == 172.5
    assert s.tm_suggestion(points, 2, "S", current=165) == 172.5
    assert s.tm_suggestion(points, 2, "S", current=172.5) is None  # różnica poniżej 2,5 kg
    assert s.suggest_tm(points, 1, "S") is None


def test_suggestion_after_attempts_can_go_down():
    points = [s.LiftPoint(dt.date(2026, 12, 29), "S", 170, 10, 170, 2, "t10", "att")]
    assert s.tm_suggestion(points, 3, "S", current=180) == 170


def test_last_result_prefers_same_gym():
    plan = make_plan()
    season = s.build_season(plan, MEET, None)
    at = dt.datetime(2026, 10, 30, 18, tzinfo=UTC)
    logs = {
        "t01-D1": log({2: {"kg": 20, "reps": 15}}, gym="Siłownia A"),
        "t01-D2": log({0: {"kg": 25, "reps": 12, "rpe": 8}}, at=at, gym="Siłownia  B"),
    }
    current = season[1].sessions[0]
    last = s.last_result(season, logs, "Face pull", "siłownia a", current)
    assert (last["kg"], last["gym"], last["date"]) == (20, "Siłownia A", dt.date(2026, 10, 26))
    latest = s.last_result(season, logs, "Face pull", None, current)
    assert (latest["kg"], latest["shown"]) == (25, dt.date(2026, 10, 30))  # data zapisu
    # Sama sesja i późniejsze się nie liczą.
    assert s.last_result(season, logs, "Face pull", None, season[0].sessions[0]) is None
    assert s.known_gyms(season, logs) == ["Siłownia  B", "Siłownia A"]


def test_auto_locate():
    season = s.build_season(make_plan(), MEET, None)
    monday = dt.date(2026, 11, 2)
    # Bez wpisów: dzisiejsza sesja albo najbliższa następna („dziś wolne").
    assert s.auto_locate(season, {}, dt.date(2026, 10, 26), dt.datetime.now(UTC)) == (0, 0, False)
    assert s.auto_locate(season, {}, dt.date(2026, 10, 27), dt.datetime.now(UTC)) == (0, 1, True)
    # Po zapisanej sesji pokazuje następną w kolejności, nawet gdy kalendarz mówi co innego.
    at = dt.datetime(2026, 11, 2, 18, tzinfo=UTC)
    logs = {"t01-D2": log({0: {"kg": 25}}, at=at)}
    late = dt.datetime(2026, 11, 3, 9, tzinfo=UTC)
    assert s.auto_locate(season, logs, monday, late) == (1, 0, False)
    # Zapisana przed chwilą (do 8 godzin) zostaje na ekranie.
    soon = dt.datetime(2026, 11, 2, 20, tzinfo=UTC)
    assert s.auto_locate(season, logs, monday, soon) == (0, 1, False)
    # Następna sesja dalej niż 6 dni od dziś: wraca do kalendarza.
    far = dt.date(2026, 11, 25)
    assert s.auto_locate(season, logs, far, late) == (2, 0, True)
    assert s.current_week(season, dt.date(2026, 11, 4)) == 1
    assert s.current_week(season, dt.date(2026, 11, 20)) is None


def test_plan_errors():
    assert s.plan_errors(make_plan()) == []
    assert s.plan_errors([]) == ["Plik planu nie jest obiektem JSON."]
    broken = make_plan()
    broken["weeks"][0]["days"][0]["code"] = "BARDZODLUGIKOD"
    del broken["training_max"]
    errors = s.plan_errors(broken)
    assert "Brak maksów treningowych fazy 1 (training_max.phase_1)." in errors
    assert any("za długi kod dnia" in e for e in errors)


def test_number():
    assert s.number("92,5") == 92.5
    assert s.number(True) is None
    assert s.number("") is None
    assert s.number(float("nan")) is None
