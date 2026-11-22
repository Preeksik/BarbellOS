"""Ponowne użycie (22.11.2026): szacunek AI staje się produktem, posiłek da się skopiować."""

import datetime as dt
import uuid

import pytest

from app.core.diary import per_100_of_entry, recent_meals

DONUT = {
    "name": "Pączek z polewą z Dobrej piekarni",
    "per_100": {"kcal": 400, "protein_g": 5, "fat_g": 20, "carbs_g": 50},
    "micros_per_100": {"calcium": 30},
}


def _put(client, entry_id=None, **body):
    payload = {"date": "2026-11-21", "meal_slot": "snack", "amount": 80, **body}
    return client.put(f"/api/diary/entries/{entry_id or uuid.uuid4()}", json=payload)


# ====================================================================== core


def test_per_100_of_entry_restores_values_and_keeps_missing():
    values = {"kcal": 600, "protein_g": 24, "fat_g": None}
    micros = {"vit_c": {"amount": 6.0, "source": "estimated"}}
    per_100, micros_100 = per_100_of_entry(values, micros, 400)
    assert per_100 == {"kcal": 150, "protein_g": 6, "fat_g": None}
    assert micros_100 == {"vit_c": (1.5, "estimated")}


def test_recent_meals_newest_day_first_then_slot_order():
    d1, d2 = dt.date(2026, 11, 20), dt.date(2026, 11, 21)
    entries = [
        {"date": d1, "meal_slot": "lunch"},
        {"date": d2, "meal_slot": "dinner"},
        {"date": d2, "meal_slot": "breakfast"},
        {"date": d1, "meal_slot": "lunch"},
    ]
    assert recent_meals(entries) == [
        (d2, "breakfast", [2]),
        (d2, "dinner", [1]),
        (d1, "lunch", [0, 3]),
    ]
    assert recent_meals(entries, limit=1) == [(d2, "breakfast", [2])]


# ====================================================================== szacunek -> produkt


def test_ai_estimate_creates_a_reusable_product(logged_in):
    entry = _put(logged_in, estimate=DONUT, source="photo").json()
    assert entry["food_id"] is not None
    assert entry["macro_source"] == "estimated"
    assert entry["values"]["kcal"] == pytest.approx(320)  # 80 g z 400 kcal/100 g

    food = logged_in.get(f"/api/foods/{entry['food_id']}").json()
    assert food["name"] == DONUT["name"]
    assert (food["origin"], food["macro_source"]) == ("ai", "estimated")
    assert food["per_100"]["kcal"] == 400 and food["per_100"]["sugars_g"] is None
    assert {m["nutrient_id"]: m["source"] for m in food["micros"]} == {"calcium": "estimated"}

    # Wyszukiwarka i „Ostatnie" go znają, a zapisany posiłek go przyjmuje.
    found = logged_in.get("/api/foods/search", params={"q": "pączek"}).json()["foods"]
    assert [f["id"] for f in found] == [food["id"]]
    meal = {"name": "Deser", "items": [{"food_id": food["id"], "amount": 80}]}
    assert logged_in.put(f"/api/meals/{uuid.uuid4()}", json=meal).status_code == 204


def test_same_estimate_name_reuses_the_product(logged_in):
    first = _put(logged_in, estimate=DONUT, source="photo").json()
    newer = {**DONUT, "name": "pączek z polewą z dobrej  piekarni", "per_100": {"kcal": 420}}
    second = _put(logged_in, estimate=newer, source="text").json()
    assert second["food_id"] == first["food_id"]
    food = logged_in.get(f"/api/foods/{first['food_id']}").json()
    assert food["per_100"]["kcal"] == 420  # najnowszy szacunek
    # Zamrożony wcześniejszy wpis się nie zmienia.
    day = logged_in.get("/api/diary/2026-11-21").json()
    assert sorted(e["values"]["kcal"] for e in day["entries"]) == pytest.approx([320, 336])


def test_user_corrected_product_is_not_overwritten_by_a_new_estimate(logged_in):
    food_id = _put(logged_in, estimate=DONUT, source="photo").json()["food_id"]
    fixed = {"name": DONUT["name"], "unit": "g", "per_100": {"kcal": 380}}
    assert logged_in.put(f"/api/foods/{food_id}", json=fixed).status_code == 200
    _put(logged_in, estimate={**DONUT, "per_100": {"kcal": 999}}, source="text")
    assert logged_in.get(f"/api/foods/{food_id}").json()["per_100"]["kcal"] == 380


def test_retried_estimate_and_later_edit_keep_one_product(logged_in):
    entry_id = uuid.uuid4()
    first = _put(logged_in, entry_id, estimate=DONUT, source="photo").json()
    again = _put(logged_in, entry_id, estimate=DONUT, source="photo").json()  # powtórka z kolejki
    assert again["food_id"] == first["food_id"]
    # Telefon zmienia ilość, zanim poznał produkt (food_id None): wpis zostaje przy produkcie.
    edited = _put(logged_in, entry_id, amount=40, source="photo").json()
    assert edited["food_id"] == first["food_id"]
    assert edited["values"]["kcal"] == pytest.approx(160)
    foods = logged_in.get("/api/foods/search", params={"q": "pączek"}).json()["foods"]
    assert len(foods) == 1


# ====================================================================== kopiowanie posiłku


def test_copy_entry_to_another_day_keeps_frozen_values(logged_in):
    original = _put(logged_in, estimate=DONUT, source="photo").json()
    # Produkt poprawiony po fakcie: kopia bierze wartości z wpisu, a nie z produktu.
    fixed = {"name": DONUT["name"], "unit": "g", "per_100": {"kcal": 100}}
    logged_in.put(f"/api/foods/{original['food_id']}", json=fixed)

    copy_id = uuid.uuid4()
    body = {"date": "2026-11-22", "meal_slot": "lunch", "amount": 80, "source": "copy",
            "copy_of": original["id"]}  # fmt: skip
    copy = logged_in.put(f"/api/diary/entries/{copy_id}", json=body).json()
    assert copy["food_id"] == original["food_id"]
    assert copy["values"]["kcal"] == pytest.approx(320)
    assert (copy["date"], copy["meal_slot"], copy["source"]) == ("2026-11-22", "lunch", "copy")
    # Powtórka z kolejki offline niczego nie dubluje.
    logged_in.put(f"/api/diary/entries/{copy_id}", json=body)
    assert len(logged_in.get("/api/diary/2026-11-22").json()["entries"]) == 1

    missing = {**body, "copy_of": str(uuid.uuid4())}
    assert logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=missing).status_code == 404


def test_recent_meals_lists_groups_with_entries(logged_in):
    _put(logged_in, date="2026-11-20", meal_slot="lunch", estimate=DONUT, source="photo")
    spaghetti = {"name": "Spaghetti z leczo", "per_100": {"kcal": 150}}
    _put(logged_in, date="2026-11-21", meal_slot="lunch", amount=400, estimate=spaghetti,
         source="text")  # fmt: skip
    _put(logged_in, date="2026-11-21", meal_slot="lunch", amount=100, estimate=DONUT, source="text")

    meals = logged_in.get("/api/diary/recent-meals/2026-11-22").json()
    assert [(m["date"], m["meal_slot"], len(m["entries"])) for m in meals] == [
        ("2026-11-21", "lunch", 2),
        ("2026-11-20", "lunch", 1),
    ]
    assert meals[0]["kcal"] == pytest.approx(600 + 400)
    assert [e["food_name"] for e in meals[0]["entries"]][0] == "Spaghetti z leczo"
    # Dzień dalej niż dwa tygodnie wstecz nie wchodzi.
    assert logged_in.get("/api/diary/recent-meals/2026-12-10").json() == []
