import uuid

import pytest

from app.core.diary import day_totals, freeze_portion, scale_portion

EAN = "5900000000015"  # produkt z conftest: 97 kcal, B 11, T 5, nasycone 3,5, W 2, błonnik brak
DAY = "2026-11-16"


# ---------- logika ----------


def test_freeze_portion_keeps_missing_values_missing():
    values, micros = freeze_portion(
        {"kcal": 97, "protein_g": 11, "fiber_g": None}, {"calcium": (80.0, "label")}, 150
    )
    assert values["kcal"] == pytest.approx(145.5)
    assert values["protein_g"] == pytest.approx(16.5)
    assert values["fiber_g"] is None
    assert values["salt_g"] is None  # klucza nie było: brak danych, nie zero
    assert micros == {"calcium": {"amount": 120.0, "source": "label"}}


def test_scale_portion():
    values, micros = scale_portion(
        {"kcal": 100.0, "fiber_g": None}, {"calcium": {"amount": 50.0, "source": "label"}}, 1.5
    )
    assert values == {"kcal": 150.0, "fiber_g": None}
    assert micros["calcium"] == {"amount": 75.0, "source": "label"}
    assert scale_portion({"kcal": 1.0}, None, 2)[1] == {}


def test_day_totals_group_by_meal_in_fixed_order():
    result = day_totals(
        [
            {"meal_slot": "dinner", "kcal": 500, "protein_g": 30},
            {"meal_slot": "breakfast", "kcal": 300, "protein_g": None},
            {"meal_slot": "dinner", "kcal": 200, "protein_g": 10},
        ]
    )
    assert result["totals"]["kcal"] == 1000
    assert result["totals"]["protein_g"] == 40
    assert list(result["by_slot"]) == ["breakfast", "dinner"]
    assert result["by_slot"]["dinner"]["kcal"] == 700
    assert day_totals([]) == {"totals": dict.fromkeys(result["totals"], 0.0), "by_slot": {}}


# ---------- API ----------


@pytest.fixture
def food(logged_in):
    return logged_in.get(f"/api/foods/barcode/{EAN}").json()


def _put(client, food_id, entry_id=None, **changes):
    entry_id = entry_id or str(uuid.uuid4())
    body = {"date": DAY, "meal_slot": "lunch", "food_id": food_id, "amount": 200, **changes}
    return entry_id, client.put(f"/api/diary/entries/{entry_id}", json=body)


def test_diary_requires_login(client):
    assert client.get(f"/api/diary/{DAY}").status_code == 401
    assert client.put(f"/api/diary/entries/{uuid.uuid4()}", json={}).status_code == 401
    assert client.delete(f"/api/diary/entries/{uuid.uuid4()}").status_code == 401


def test_empty_day(logged_in):
    day = logged_in.get(f"/api/diary/{DAY}").json()
    assert (day["entries"], day["by_slot"], day["totals"]["kcal"]) == ([], {}, 0)


def test_add_entry_freezes_portion_values(logged_in, food):
    entry_id, response = _put(logged_in, food["id"])
    assert response.status_code == 200
    entry = response.json()
    assert (entry["id"], entry["food_name"], entry["amount"], entry["unit"]) == (
        entry_id, "Serek wiejski", 200, "g",
    )  # fmt: skip
    assert entry["values"]["kcal"] == pytest.approx(194)
    assert entry["values"]["sat_fat_g"] == pytest.approx(7)
    assert entry["values"]["fiber_g"] is None

    day = logged_in.get(f"/api/diary/{DAY}").json()
    assert [e["id"] for e in day["entries"]] == [entry_id]
    assert day["totals"]["kcal"] == pytest.approx(194)
    assert day["by_slot"]["lunch"]["protein_g"] == pytest.approx(22)


def test_history_does_not_change_when_product_is_corrected(logged_in, food):
    entry_id, _ = _put(logged_in, food["id"])
    corrected = {**food["per_100"], "kcal": 150}
    update = {"name": food["name"], "brand": food["brand"], "unit": "g", "per_100": corrected}
    assert logged_in.put(f"/api/foods/{food['id']}", json=update).status_code == 200

    old = logged_in.get(f"/api/diary/{DAY}").json()["entries"][0]
    assert old["values"]["kcal"] == pytest.approx(194)  # wpis sprzed poprawki zostaje

    _, new = _put(logged_in, food["id"])
    assert new.json()["values"]["kcal"] == pytest.approx(300)  # nowy wpis liczy się po nowemu

    # zmiana ilości starego wpisu skaluje zamrożone wartości, nie sięga po nowe
    _, changed = _put(logged_in, food["id"], entry_id, amount=100)
    assert changed.json()["values"]["kcal"] == pytest.approx(97)


def test_put_is_idempotent(logged_in, food):
    entry_id, first = _put(logged_in, food["id"])
    _, second = _put(logged_in, food["id"], entry_id)
    assert first.json() == second.json()
    assert len(logged_in.get(f"/api/diary/{DAY}").json()["entries"]) == 1


def test_entry_can_move_to_another_meal_and_day(logged_in, food):
    entry_id, _ = _put(logged_in, food["id"])
    _put(logged_in, food["id"], entry_id, meal_slot="dinner", date="2026-11-17")
    assert logged_in.get(f"/api/diary/{DAY}").json()["entries"] == []
    moved = logged_in.get("/api/diary/2026-11-17").json()
    assert list(moved["by_slot"]) == ["dinner"]
    assert moved["entries"][0]["values"]["kcal"] == pytest.approx(194)


def test_entries_are_ordered_by_meal_then_time(logged_in, food):
    dinner, _ = _put(logged_in, food["id"], meal_slot="dinner")
    breakfast, _ = _put(logged_in, food["id"], meal_slot="breakfast")
    snack, _ = _put(logged_in, food["id"], meal_slot="snack")
    day = logged_in.get(f"/api/diary/{DAY}").json()
    assert [e["id"] for e in day["entries"]] == [breakfast, snack, dinner]
    assert day["totals"]["kcal"] == pytest.approx(3 * 194)


def test_drink_keeps_millilitres(logged_in, food):
    update = {"name": "Napój", "brand": None, "unit": "ml", "per_100": food["per_100"]}
    logged_in.put(f"/api/foods/{food['id']}", json=update)
    _, response = _put(logged_in, food["id"], amount=330)
    assert (response.json()["unit"], response.json()["amount"]) == ("ml", 330)


def test_delete_is_idempotent(logged_in, food):
    entry_id, _ = _put(logged_in, food["id"])
    assert logged_in.delete(f"/api/diary/entries/{entry_id}").status_code == 204
    assert logged_in.delete(f"/api/diary/entries/{entry_id}").status_code == 204
    assert logged_in.get(f"/api/diary/{DAY}").json()["entries"] == []


@pytest.mark.parametrize(
    "changes",
    [{"amount": 0}, {"amount": -5}, {"amount": 6000}, {"meal_slot": "brunch"}, {"date": "wczoraj"}],
)
def test_invalid_entries_are_rejected(logged_in, food, changes):
    assert _put(logged_in, food["id"], **changes)[1].status_code == 422


def test_unknown_food(logged_in):
    assert _put(logged_in, 999)[1].status_code == 404
    assert logged_in.get("/api/diary/nie-data").status_code == 422
