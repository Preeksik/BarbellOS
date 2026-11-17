"""Profil użytkownika i plan: zapotrzebowanie kaloryczne i cele makroskładników."""

from dataclasses import replace
from datetime import date

import pytest

from app.core.profile import (
    Profile,
    age_on,
    bmr_mifflin,
    plan_for,
    profile_errors,
)

TODAY = date(2026, 11, 17)
# 28 lat, 180 cm, 80 kg, 3–5 treningów w tygodniu, redukcja 0,5 kg na tydzień.
BASE = Profile("male", date(1998, 5, 10), 180, 80, "moderate", "lose", 0.5)


def test_age_counts_full_years():
    assert age_on(date(1998, 11, 17), TODAY) == 28  # urodziny dziś
    assert age_on(date(1998, 11, 18), TODAY) == 27  # urodziny jutro
    assert age_on(date(2000, 2, 29), date(2026, 2, 28)) == 25


def test_bmr_mifflin_st_jeor():
    # 10 × 80 + 6,25 × 180 − 5 × 28 + 5 = 1790
    assert bmr_mifflin("male", 80, 180, 28) == pytest.approx(1790)
    assert bmr_mifflin("female", 60, 165, 30) == pytest.approx(1320.25)


def test_plan_for_cut():
    plan = plan_for(BASE, TODAY)
    assert (plan.age, plan.bmr, plan.tdee) == (28, 1790, 2774)  # 1790 × 1,55
    assert plan.kcal == 2220  # 2774 − 550 (0,5 kg × 7700 / 7), do 10 kcal
    assert plan.adjustment == -554
    g = plan.goals
    assert g["protein_g"] == 175  # 2,2 g/kg × 80, do 5 g
    assert g["fat_g"] == 60  # 25% × 2220 / 9
    assert g["carbs_g"] == 245  # (2220 − 175 × 4 − 60 × 9) / 4
    assert g["fiber_g"] == 31  # 14 g / 1000 kcal
    assert g["sat_fat_g"] == 25  # 10% kalorii
    assert g["salt_g"] == 5
    assert g["sugars_g"] is None
    assert plan.warnings == []
    # Każda liczba ma wyjaśnienie, po polsku (przecinek dziesiętny).
    assert any("1790 × 1,55 = 2774" in note for note in plan.notes)
    assert any("Deficyt" in note and "0,5 kg" in note for note in plan.notes)


def test_macros_add_up_to_calories():
    for goal, pace in (("lose", 0.5), ("maintain", 0.0), ("gain", 0.25)):
        plan = plan_for(replace(BASE, goal=goal, pace_kg_week=pace), TODAY)
        g = plan.goals
        kcal_from_macros = g["protein_g"] * 4 + g["fat_g"] * 9 + g["carbs_g"] * 4
        assert abs(kcal_from_macros - plan.kcal) <= 40, goal  # zaokrąglenia do 5 g


def test_maintain_and_gain():
    maintain = plan_for(replace(BASE, goal="maintain", pace_kg_week=0.0), TODAY)
    assert maintain.kcal == 2770
    assert maintain.goals["protein_g"] == 145  # 1,8 g/kg domyślnie
    gain = plan_for(replace(BASE, goal="gain", pace_kg_week=0.25), TODAY)
    assert gain.kcal == 3050  # 2774 + 275
    assert gain.adjustment > 0


def test_fast_cut_is_capped_at_one_percent_of_body_weight():
    plan = plan_for(replace(BASE, pace_kg_week=1.0), TODAY)
    assert plan.pace_kg_week == 0.75  # 1% z 80 kg = 0,8
    assert plan.kcal == 1950
    assert "ponad 1% masy ciała" in plan.warnings[0]


def test_cut_never_goes_below_resting_metabolism():
    # Siedzący tryb: zapotrzebowanie 1,2 × BMR, więc deficyt 0,75 kg zszedłby poniżej BMR.
    sitting = replace(BASE, activity="sedentary", pace_kg_week=0.75)
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
    "activity": "moderate",
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
    [{"height_cm": 90}, {"sex": "other"}, {"activity": "extreme"}, {"pace_kg_week": 2}],
)
def test_invalid_profile_is_rejected(logged_in, changes):
    assert logged_in.put("/api/profile", json={**BODY, **changes}).status_code == 422
    assert logged_in.get("/api/profile").json()["profile"] is None
