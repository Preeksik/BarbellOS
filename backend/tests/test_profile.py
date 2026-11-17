"""Profil użytkownika i plan: zapotrzebowanie kaloryczne i cele makroskładników."""

from dataclasses import replace
from datetime import date

import pytest

from app.core.profile import (
    Profile,
    age_on,
    bmr_mifflin,
    exercise_kcal_per_day,
    plan_for,
    profile_errors,
    steps_kcal,
)

TODAY = date(2026, 11, 17)
# 28 lat, 180 cm, 80 kg; student dojeżdżający autem, 5000 kroków, 4 treningi siłowe
# po 75 minut, bez cardio; redukcja 0,5 kg na tydzień.
BASE = Profile(
    sex="male",
    birth_date=date(1998, 5, 10),
    height_cm=180,
    weight_kg=80,
    lifestyle="sitting",
    steps_per_day=5000,
    strength_sessions_week=4,
    strength_minutes=75,
    cardio_minutes_week=0,
    goal="lose",
    pace_kg_week=0.5,
)


def test_age_counts_full_years():
    assert age_on(date(1998, 11, 17), TODAY) == 28  # urodziny dziś
    assert age_on(date(1998, 11, 18), TODAY) == 27  # urodziny jutro
    assert age_on(date(2000, 2, 29), date(2026, 2, 28)) == 25


def test_bmr_mifflin_st_jeor():
    # 10 × 80 + 6,25 × 180 − 5 × 28 + 5 = 1790
    assert bmr_mifflin("male", 80, 180, 28) == pytest.approx(1790)
    assert bmr_mifflin("female", 60, 165, 30) == pytest.approx(1320.25)


def test_steps_kcal():
    # Krok 0,415 × 180 cm = 74,7 cm; 5000 kroków = 3,7 km; 0,5 kcal × 80 kg × 3,7 km.
    kcal, km = steps_kcal(5000, "male", 180, 80)
    assert km == pytest.approx(3.735)
    assert kcal == pytest.approx(149.4)
    assert steps_kcal(10_000, "male", 180, 80)[0] == pytest.approx(2 * kcal)
    assert steps_kcal(0, "female", 165, 60) == (0, 0)


def test_exercise_kcal_is_counted_above_rest():
    # 4 × 75 min = 5 h tygodniowo; (5 MET − 1) × 80 kg × 5 h ÷ 7 dni.
    assert exercise_kcal_per_day(5.0, 300, 80) == pytest.approx(228.6, abs=0.1)
    assert exercise_kcal_per_day(7.0, 0, 80) == 0


def test_energy_parts_add_up():
    plan = plan_for(BASE, TODAY)
    parts = {part.key: part for part in plan.parts}
    assert list(parts) == ["bmr", "lifestyle", "steps", "strength", "cardio", "tef"]
    assert parts["bmr"].kcal == 1790
    assert parts["lifestyle"].kcal == 268  # 15% z 1790
    assert parts["steps"].kcal == 149
    assert parts["steps"].detail == "5 000 kroków ≈ 3,7 km"
    assert parts["strength"].kcal == 229
    assert parts["cardio"].kcal == 0
    assert parts["tef"].kcal == 271  # 10% całości
    assert plan.tdee == 2707
    assert abs(sum(part.kcal for part in plan.parts) - plan.tdee) <= 3  # zaokrąglenia


def test_lifestyle_changes_only_its_own_part():
    office = plan_for(BASE, TODAY)
    standing = plan_for(replace(BASE, lifestyle="standing"), TODAY)
    diff = {a.key: b.kcal - a.kcal for a, b in zip(office.parts, standing.parts, strict=True)}
    assert diff["lifestyle"] == pytest.approx(0.25 * 1790, abs=1)  # 40% − 15%
    assert diff["steps"] == diff["strength"] == 0


def test_whole_expenditure_stays_in_who_pal_ranges():
    """Całość względem BMR ma pasować do zakresów PAL FAO/WHO/UNU (1,4–2,4)."""
    student = plan_for(BASE, TODAY)
    assert 1.4 <= student.tdee / student.bmr <= 1.69  # siedzący
    builder = replace(BASE, lifestyle="physical", steps_per_day=12_000)
    plan = plan_for(builder, TODAY)
    assert 1.9 <= plan.tdee / plan.bmr <= 2.4  # bardzo aktywny


def test_plan_for_cut():
    plan = plan_for(BASE, TODAY)
    assert (plan.age, plan.bmr, plan.tdee) == (28, 1790, 2707)
    assert plan.kcal == 2160  # 2707 − 550 (0,5 kg × 7700 / 7), do 10 kcal
    assert plan.adjustment == -547
    g = plan.goals
    assert g["protein_g"] == 175  # 2,2 g/kg × 80, do 5 g
    assert g["fat_g"] == 60  # 25% × 2160 / 9
    assert g["carbs_g"] == 230  # (2160 − 175 × 4 − 60 × 9) / 4
    assert g["fiber_g"] == 30  # 14 g / 1000 kcal
    assert g["sat_fat_g"] == 24  # 10% kalorii
    assert g["salt_g"] == 5
    assert g["sugars_g"] is None
    assert plan.warnings == []
    # Każda liczba ma wyjaśnienie, po polsku (przecinek dziesiętny).
    assert any("równanie ACSM" in note and "149 kcal" in note for note in plan.notes)
    assert any("1,51 × przemiana spoczynkowa" in note for note in plan.notes)
    assert any("Deficyt" in note and "0,5 kg" in note for note in plan.notes)


def test_macros_add_up_to_calories():
    for goal, pace in (("lose", 0.5), ("maintain", 0.0), ("gain", 0.25)):
        plan = plan_for(replace(BASE, goal=goal, pace_kg_week=pace), TODAY)
        g = plan.goals
        kcal_from_macros = g["protein_g"] * 4 + g["fat_g"] * 9 + g["carbs_g"] * 4
        assert abs(kcal_from_macros - plan.kcal) <= 40, goal  # zaokrąglenia do 5 g


def test_maintain_and_gain():
    maintain = plan_for(replace(BASE, goal="maintain", pace_kg_week=0.0), TODAY)
    assert maintain.kcal == 2710
    assert maintain.goals["protein_g"] == 145  # 1,8 g/kg domyślnie
    gain = plan_for(replace(BASE, goal="gain", pace_kg_week=0.25), TODAY)
    assert gain.kcal == 2980  # 2707 + 275
    assert gain.adjustment > 0


def test_fast_cut_is_capped_at_one_percent_of_body_weight():
    plan = plan_for(replace(BASE, pace_kg_week=1.0), TODAY)
    assert plan.pace_kg_week == 0.75  # 1% z 80 kg = 0,8
    assert plan.kcal == 1880
    assert "ponad 1% masy ciała" in plan.warnings[0]


def test_cut_never_goes_below_resting_metabolism():
    # Bez kroków i treningów zapotrzebowanie to ok. 1,28 × BMR: deficyt 0,75 kg schodzi niżej.
    sitting = replace(BASE, steps_per_day=0, strength_sessions_week=0, pace_kg_week=0.75)
    plan = plan_for(sitting, TODAY)
    assert plan.kcal == 1790
    assert plan.pace_kg_week < 0.75
    assert "poniżej przemiany spoczynkowej" in plan.warnings[0]


def test_custom_protein():
    plan = plan_for(replace(BASE, protein_g_per_kg=2.6), TODAY)
    assert plan.protein_g_per_kg == 2.6
    assert plan.goals["protein_g"] == 210  # 2,6 × 80 = 208 → 210


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"birth_date": date(2020, 1, 1)}, "Wiek musi wynosić"),
        ({"height_cm": 300}, "Wzrost"),
        ({"weight_kg": 20}, "Masa ciała"),
        ({"pace_kg_week": 0.3}, "Tempo dla tego celu: 0,25, 0,5, 0,75, 1 kg"),
        ({"goal": "maintain", "pace_kg_week": 0.5}, "Tempo dla tego celu: 0 kg"),
        ({"protein_g_per_kg": 5}, "Białko musi wynosić od 1,2 do 3,1"),
        ({"steps_per_day": 50_000}, "Średnia kroków"),
        ({"strength_sessions_week": 20}, "Treningów siłowych"),
        ({"strength_minutes": 5}, "Trening siłowy musi trwać"),
        ({"cardio_minutes_week": 3000}, "Cardio"),
    ],
)
def test_profile_errors(changes, fragment):
    assert any(fragment in e for e in profile_errors(replace(BASE, **changes), TODAY))


def test_valid_profile_has_no_errors():
    assert profile_errors(BASE, TODAY) == []


# ---------- API ----------

BODY = {
    "sex": "male",
    "birth_date": "1998-05-10",
    "height_cm": 180,
    "weight_kg": 80,
    "lifestyle": "sitting",
    "steps_per_day": 5000,
    "strength_sessions_week": 4,
    "strength_minutes": 75,
    "goal": "lose",
    "pace_kg_week": 0.5,
}


def test_profile_requires_login(client):
    assert client.get("/api/profile").status_code == 401
    assert client.put("/api/profile", json=BODY).status_code == 401


def test_empty_profile(logged_in):
    assert logged_in.get("/api/profile").json() == {"profile": None, "plan": None}


def test_save_profile_returns_plan_and_is_idempotent(logged_in):
    first = logged_in.put("/api/profile", json=BODY)
    assert first.status_code == 200
    body = first.json()
    assert body["profile"]["weight_kg"] == 80
    assert body["profile"]["protein_g_per_kg"] is None
    assert body["plan"]["bmr"] == pytest.approx(1790, abs=10)  # wiek zależy od dzisiejszej daty
    assert body["plan"]["goals"]["salt_g"] == 5
    assert [part["key"] for part in body["plan"]["parts"]][:3] == ["bmr", "lifestyle", "steps"]
    assert body["plan"]["goals"]["sugars_g"] is None

    again = logged_in.put("/api/profile", json={**BODY, "weight_kg": 78}).json()
    assert again["profile"]["weight_kg"] == 78
    assert again["plan"]["kcal"] < body["plan"]["kcal"]
    assert logged_in.get("/api/profile").json() == again


def test_profile_does_not_change_targets_by_itself(logged_in):
    """Plan to propozycja: cele dzienne zmienia dopiero zatwierdzenie użytkownika."""
    logged_in.put("/api/profile", json=BODY)
    assert logged_in.get("/api/targets/2026-11-17").json()["date_from"] is None


def test_plan_goals_are_accepted_as_daily_targets(logged_in):
    goals = logged_in.put("/api/profile", json=BODY).json()["plan"]["goals"]
    saved = logged_in.put("/api/targets/2026-11-17", json={"goals": goals})
    assert saved.status_code == 200
    assert saved.json()["goals"] == goals


@pytest.mark.parametrize(
    "changes",
    [
        {"height_cm": 90},
        {"sex": "other"},
        {"lifestyle": "extreme"},
        {"pace_kg_week": 2},
        {"steps_per_day": -1},
    ],
)
def test_invalid_profile_is_rejected(logged_in, changes):
    assert logged_in.put("/api/profile", json={**BODY, **changes}).status_code == 422
    assert logged_in.get("/api/profile").json()["profile"] is None
