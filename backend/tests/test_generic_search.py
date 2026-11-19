"""Wyszukiwarka 19.11.2026: produkty podstawowe z tabel USDA i kolejność dużej bazy."""

import pytest

from app.ai.provider import ProviderUnavailable
from app.api.deps import get_fdc_client
from app.core.micros import generic_candidates
from app.core.search import order_hits
from app.fdc.client import FdcError, FdcFood, parse_food
from app.services import generic_search

# ====================================================================== core


def test_order_hits_puts_the_vegetable_before_chips_and_spices():
    hits = [
        ("Chipsy o smaku papryki", "Lay's", 536),
        ("Papryka słodka mielona", "Kamis", 289),
        ("Papryka czerwona", None, 31),
        ("Mieszanka warzyw z papryką", None, 40),
        ("Czerwona oranżada", None, 40),
    ]
    # Krótsza nazwa zaczynająca się od zapytania wyżej; „papryką" bez ogonków to „papryka".
    # Chipsy „o smaku papryki" i oranżada nie mają słowa „papryka": odpadają.
    assert order_hits("papryka", hits) == [2, 1, 3]
    # Oba słowa przed jednym; pierwsze słowo (rzeczownik) przed drugim.
    assert order_hits("papryka czerwona", hits) == [2, 1, 3, 4]


def test_order_hits_ignores_empty_query():
    assert order_hits("  ", [("Papryka", None, 30)]) == []


def test_order_hits_drops_results_without_kcal():
    hits = [("Papryka czerwona", None, None), ("Papryka żółta", None, 27)]
    assert order_hits("papryka", hits) == [1]


def test_generic_candidates_need_kcal_and_a_good_name():
    candidates = [
        (1, "Peppers, sweet, red, raw", 31),
        (2, "Peppers, sweet, red, cooked, boiled, drained, without salt", 28),
        (3, "Peppers, sweet, red, frozen", None),  # bez kalorii: odpada
        (4, "Spices, paprika", 282),  # jedno wspólne słowo z innej kategorii: odpada
    ]
    assert generic_candidates("Peppers, sweet, red", candidates) == [1, 2]
    assert generic_candidates("Peppers, sweet, red", candidates, limit=1) == [1]
    assert generic_candidates("Peppers", []) == []


def test_parse_food_reads_macros_and_salt_from_sodium():
    raw = {
        "fdcId": 170108,
        "description": "Peppers, sweet, red, raw",
        "dataType": "SR Legacy",
        "foodNutrients": [
            {"nutrientNumber": "208", "value": 31, "unitName": "KCAL"},
            {"nutrientNumber": "203", "value": 0.99, "unitName": "G"},
            {"nutrientNumber": "204", "value": 0.3, "unitName": "G"},
            {"nutrientNumber": "205", "value": 6.03, "unitName": "G"},
            {"nutrientNumber": "291", "value": 2.1, "unitName": "G"},
            {"nutrientNumber": "307", "value": 4, "unitName": "MG"},
            {"nutrientNumber": "401", "value": 127.7, "unitName": "MG"},
        ],
    }
    food = parse_food(raw)
    assert food.kcal == 31
    assert food.macros == {
        "protein_g": 0.99,
        "fat_g": 0.3,
        "carbs_g": 6.03,
        "fiber_g": 2.1,
        "salt_g": 0.01,
    }
    assert "sugars_g" not in food.macros  # brak w rekordzie = brak, nie zero
    assert food.micros["vit_c"] == 127.7


# ====================================================================== API


PEPPER = FdcFood(
    170108,
    "Peppers, sweet, red, raw",
    "SR Legacy",
    31,
    {"vit_c": 127.7, "potassium": 211.0, "vit_a": 157.0, "vit_b6": 0.29, "folate": 46.0},
    {"protein_g": 0.99, "fat_g": 0.3, "carbs_g": 6.03, "fiber_g": 2.1},
)
PEPPER_BOILED = FdcFood(
    170109,
    "Peppers, sweet, red, cooked, boiled, drained, without salt",
    "SR Legacy",
    28,
    {"vit_c": 171.0},
    {"protein_g": 0.92},
)
SPICE = FdcFood(171329, "Spices, paprika", "SR Legacy", 282, {"iron": 21.1})


class GenericFdc:
    def __init__(self):
        self.queries: list[str] = []
        self.records = [SPICE, PEPPER, PEPPER_BOILED]
        self.error: Exception | None = None

    def search(self, query, page_size=10):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.records

    def food(self, fdc_id):
        if self.error:
            raise self.error
        return next(r for r in self.records if r.fdc_id == fdc_id)


@pytest.fixture
def generic_fdc(client):
    generic_search.clear_cache()
    fake = GenericFdc()
    client.app.dependency_overrides[get_fdc_client] = lambda: fake
    yield fake
    generic_search.clear_cache()


def test_generic_search_translates_ranks_and_names_in_polish(logged_in, label_ai, generic_fdc):
    label_ai.outcomes = [
        {"query_en": "Peppers, sweet, red"},
        {"names_pl": ["Papryka czerwona, surowa", "Papryka czerwona, gotowana"]},
    ]
    response = logged_in.get("/api/foods/search/generic", params={"q": "papryka czerwona"})
    assert response.status_code == 200
    hits = response.json()
    assert [(h["fdc_id"], h["name"]) for h in hits] == [
        (170108, "Papryka czerwona, surowa"),
        (170109, "Papryka czerwona, gotowana"),
    ]
    assert hits[0]["kcal"] == 31 and hits[0]["protein_g"] == 0.99
    assert generic_fdc.queries == ["Peppers, sweet, red"]
    # Polecenie dla modelu nie zawiera identyfikatorów, tylko opisy (AGENTS.md, zasada 8).
    assert "170108" not in label_ai.calls[1]["prompt"]

    # Powtórka (także z inną wielkością liter) nie woła ani modelu, ani USDA.
    again = logged_in.get("/api/foods/search/generic", params={"q": "Papryka  Czerwona"})
    assert again.json() == hits
    assert len(label_ai.calls) == 2 and len(generic_fdc.queries) == 1
    usage = logged_in.get("/api/ai/usage").json()
    assert {t["task"] for t in usage["by_task"]} >= {"food_query", "generic_names"}


def test_generic_search_keeps_one_hit_per_polish_name(logged_in, label_ai, generic_fdc):
    label_ai.outcomes = [
        {"query_en": "Peppers, sweet, red"},
        {"names_pl": ["Papryka czerwona, surowa", "Papryka Czerwona,  surowa"]},
    ]
    hits = logged_in.get("/api/foods/search/generic", params={"q": "papryka"}).json()
    assert [h["fdc_id"] for h in hits] == [170108]


def test_generic_search_falls_back_to_usda_names(logged_in, label_ai, generic_fdc):
    # Model zwrócił złą liczbę nazw: zostają opisy USDA zamiast zgadywania, która jest która.
    label_ai.outcomes = [{"query_en": "Peppers, sweet, red"}, {"names_pl": ["Papryka"]}]
    hits = logged_in.get("/api/foods/search/generic", params={"q": "papryka"}).json()
    assert [h["name"] for h in hits] == [PEPPER.description, PEPPER_BOILED.description]


def test_generic_search_errors(logged_in, label_ai, generic_fdc):
    label_ai.outcomes = [ProviderUnavailable("model padł")] * 4
    response = logged_in.get("/api/foods/search/generic", params={"q": "papryka"})
    assert response.status_code == 503
    label_ai.outcomes = [{"query_en": "Peppers"}]
    generic_fdc.error = FdcError("brak sieci")
    assert logged_in.get("/api/foods/search/generic", params={"q": "ogórek"}).status_code == 502
    assert logged_in.get("/api/foods/search/generic", params={"q": "og"}).status_code == 422


def test_put_generic_saves_reference_values_once(logged_in, generic_fdc):
    response = logged_in.put("/api/foods/generic/170108", json={"name": "Papryka czerwona"})
    assert response.status_code == 200
    food = response.json()
    assert food["name"] == "Papryka czerwona"
    assert food["barcode"] is None
    assert (food["origin"], food["macro_source"]) == ("fdc", "reference")
    assert food["verified_at"] is None
    assert food["per_100"]["kcal"] == 31
    assert food["per_100"]["protein_g"] == 0.99
    assert food["per_100"]["sugars_g"] is None  # brak w tabeli to NULL, nie zero
    assert food["fdc_id"] == 170108
    micros = {m["nutrient_id"]: m for m in food["micros"]}
    assert micros["vit_c"]["amount_per_100g"] == 127.7
    assert micros["vit_c"]["source"] == "reference"

    # Powtórny wybór (np. ponowione żądanie) zwraca ten sam produkt.
    again = logged_in.put("/api/foods/generic/170108", json={"name": "Papryka"})
    assert again.json()["id"] == food["id"]
    assert again.json()["name"] == "Papryka czerwona"


def test_put_generic_rejects_records_without_kcal(logged_in, generic_fdc):
    generic_fdc.records = [FdcFood(1, "Peppers, sweet, red, frozen", "SR Legacy", None)]
    assert logged_in.put("/api/foods/generic/1", json={"name": "Papryka"}).status_code == 422
    generic_fdc.error = FdcError("brak sieci")
    assert logged_in.put("/api/foods/generic/2", json={"name": "Papryka"}).status_code == 502
