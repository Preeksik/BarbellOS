"""Etap 6: mikroskładniki z tabel USDA, szacunek AI jako zapas, podsumowanie tygodnia."""

import uuid
from datetime import date

import httpx
import pytest

from app.api.deps import get_fdc_client
from app.core.micros import (
    auto_match,
    clean_micros,
    fdc_score,
    fill_missing_micros,
    kcal_plausible,
    merge_micros,
    rank_fdc,
    table_source,
)
from app.core.week import average, day_totals, micro_gaps, micro_week
from app.fdc.client import FdcClient, FdcFood, FdcRateLimited, parse_food

EAN = "5900000000015"  # serek z conftest: wapń 80 mg z etykiety


def fdc_record(fdc_id=2346396, description="Oats, whole grain, rolled, old fashioned", **extra):
    nutrients = [
        {"nutrientNumber": "208", "nutrientName": "Energy", "unitName": "KCAL", "value": 379},
        {"nutrientNumber": "304", "nutrientName": "Magnesium, Mg", "unitName": "MG", "value": 138},
        {"nutrientNumber": "303", "nutrientName": "Iron, Fe", "unitName": "MG", "value": 4.25},
        {"nutrientNumber": "435", "nutrientName": "Folate, DFE", "unitName": "UG", "value": 32},
        # Zła jednostka (µg zamiast mg): pomijamy, zamiast zgadywać przelicznik.
        {"nutrientNumber": "309", "nutrientName": "Zinc, Zn", "unitName": "UG", "value": 3640},
        {"nutrientNumber": "301", "nutrientName": "Calcium, Ca", "unitName": "MG", "value": -1},
        {"nutrientNumber": "203", "nutrientName": "Protein", "unitName": "G", "value": 13},
    ]
    return {"fdcId": fdc_id, "description": description, "dataType": "Foundation",
            "foodNutrients": nutrients, **extra}  # fmt: skip


# ====================================================================== klient USDA


def test_parse_food_maps_nutrient_numbers_and_units():
    food = parse_food(fdc_record())
    assert (food.fdc_id, food.kcal, food.data_type) == (2346396, 379, "Foundation")
    assert food.micros == {"magnesium": 138, "iron": 4.25, "folate": 32}
    assert parse_food({"description": "bez id"}) is None


def test_parse_food_uses_atwater_energy_for_foundation_foods():
    record = fdc_record()
    record["foodNutrients"][0] = {"nutrientNumber": "957", "unitName": "KCAL", "value": 375}
    assert parse_food(record).kcal == 375


def test_parse_food_reads_single_record_formats():
    """Rekord pobrany osobno ma pola `number` i `amount` (błąd z 18.11.2026: zapis bez witamin)."""
    abridged = {
        "fdcId": 174852,
        "description": "Beverages, carbonated, cola, regular",
        "dataType": "SR Legacy",
        "foodNutrients": [
            {"number": "208", "name": "Energy", "amount": 42.0, "unitName": "KCAL"},
            {"number": "301", "name": "Calcium, Ca", "amount": 2.0, "unitName": "MG"},
            {"number": "307", "name": "Sodium, Na", "amount": 4.0, "unitName": "MG"},
        ],
    }
    food = parse_food(abridged)
    assert (food.kcal, food.micros) == (42.0, {"calcium": 2.0, "sodium": 4.0})
    full = {
        "fdcId": 1,
        "foodNutrients": [
            {"nutrient": {"number": "304", "unitName": "mg"}, "amount": 27.0},
            {"nutrient": {"number": "951", "unitName": "g"}, "type": "FoodNutrient"},
        ],
    }
    assert parse_food(full).micros == {"magnesium": 27.0}


def test_cache_miss_still_saves_vitamins():
    """Bez wyników w pamięci serwer pobiera rekord osobno i nadal ma witaminy."""
    record = {
        "fdcId": 11,
        "description": "Cheese, gouda",
        "foodNutrients": [{"number": "301", "amount": 700.0, "unitName": "MG"}],
    }
    client = _client(lambda request: httpx.Response(200, json=record))
    assert client.food(11).micros == {"calcium": 700.0}


def _client(handler):
    return FdcClient("klucz", "https://fdc.test/fdc", transport=httpx.MockTransport(handler))


def test_client_search_and_cached_choice_use_one_request():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"foods": [fdc_record(), {"bez": "id"}]})

    client = _client(handler)
    (found,) = client.search("Oats, rolled")
    assert found.micros["magnesium"] == 138
    assert client.food(2346396) is found  # z pamięci: limit zapytań USDA jest mały
    assert len(seen) == 1
    params = seen[0].url.params
    assert (params["query"], params["dataType"], params["api_key"]) == (
        "Oats, rolled",
        "Foundation,SR Legacy",
        "klucz",
    )


def test_client_fetches_unknown_food_and_reports_limits():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/429"):
            return httpx.Response(429)
        return httpx.Response(200, json=fdc_record(fdc_id=11))

    client = _client(handler)
    assert client.food(11).fdc_id == 11
    assert calls == ["/fdc/v1/food/11"]
    with pytest.raises(FdcRateLimited):
        client.food(429)


def test_empty_api_key_means_demo_key():
    from app.config import Settings

    client = get_fdc_client(Settings(_env_file=None, fdc_api_key=""))
    assert client.api_key == "DEMO_KEY"


# ====================================================================== logika


def test_table_source():
    assert table_source(has_barcode=False) == "reference"  # banan: ten sam produkt
    assert table_source(has_barcode=True) == "estimated"  # serek: produkt podobny


def test_clean_micros_drops_unknown_and_impossible_values():
    raw = {"magnesium": 27, "vit_c": None, "iron": float("nan"), "vit_d": 5000, "zinc": True,
           "nieznany": 1, "folate": 20.12345}  # fmt: skip
    assert clean_micros(raw) == {"magnesium": 27, "folate": 20.123}
    assert clean_micros(None) == {}


def test_merge_micros_keeps_label_over_table():
    existing = {"calcium": (80.0, "label")}
    merged = merge_micros(existing, {"calcium": 120.0, "iron": 0.1}, "reference")
    assert merged == {"calcium": (80.0, "label"), "iron": (0.1, "reference")}
    assert merge_micros({"iron": (1.0, "estimated")}, {"iron": 2.0}, "reference") == {
        "iron": (2.0, "reference")
    }


def test_rank_fdc_beats_usda_search_order():
    """Wyszukiwarka USDA dała „Rolls, dinner, oat bran" przed płatkami (sprawdzone 18.11.2026)."""
    candidates = [
        (175028, "Rolls, dinner, oat bran"),
        (2346396, "Oats, whole grain, rolled, old fashioned"),
        (173576, "Oil, oat"),
    ]
    ranked = rank_fdc("Oats, rolled", candidates)
    assert ranked[0][0] == 2346396
    assert ranked[0][1] >= 0.5 > ranked[1][1]  # tylko płatki są podpowiadane


@pytest.mark.parametrize(
    ("query", "better", "worse"),
    [
        ("Bananas, raw", "Bananas, raw", "Bananas, dehydrated, or banana powder"),
        ("Chicken, breast, roasted", "Chicken, broilers or fryers, breast, meat only, cooked, "
         "roasted", "Chicken spread"),
        ("Tomatoes, raw", "Tomatoes, red, ripe, raw, year round average", "Soup, tomato"),
    ],
)  # fmt: skip
def test_fdc_score_prefers_the_same_head_noun(query, better, worse):
    assert fdc_score(query, better) > fdc_score(query, worse)


def test_week_totals_and_average_skip_empty_days():
    days = [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18)]
    entries = [
        {"date": days[0], "kcal": 2000, "protein_g": 150},
        {"date": days[2], "kcal": 1000, "protein_g": 50},
        {"date": days[2], "kcal": 500, "protein_g": None},
    ]
    totals = day_totals(days, entries)
    assert [(t.entries, t.totals["kcal"]) for t in totals] == [(1, 2000), (0, 0), (2, 1500)]
    avg = average(totals)
    assert avg["kcal"] == 1750  # (2000 + 1500) / 2 dni z wpisami
    assert avg["protein_g"] == 100
    assert average(day_totals(days, [])) is None


def test_micro_week_reports_coverage_and_trust():
    entries = [
        {"kcal": 600, "micros": {"magnesium": {"amount": 200, "source": "reference"}}},
        {"kcal": 300, "micros": {"magnesium": {"amount": 100, "source": "estimated"}}},
        {"kcal": 100, "micros": None},
    ]
    (mg, iodine) = micro_week(entries, {"magnesium": 375, "iodine": 150}, logged_days=2)
    assert mg.avg_amount == 150  # 300 mg w 2 dni
    assert mg.percent_rda == pytest.approx(40)
    assert (mg.share_trusted, mg.share_estimated, mg.share_missing) == (0.6, 0.3, 0.1)
    assert (iodine.avg_amount, iodine.share_missing) == (0, 1.0)
    assert micro_week([], {"iodine": 150}, 0)[0].share_missing == 0


# ====================================================================== API: dopasowanie


class FakeFdc:
    def __init__(self):
        self.queries: list[str] = []
        self.error: Exception | None = None
        self.records = [
            FdcFood(175028, "Rolls, dinner, oat bran", "SR Legacy", 236, {"iron": 4.1}),
            FdcFood(
                2346396,
                "Oats, whole grain, rolled, old fashioned",
                "Foundation",
                379,
                {"magnesium": 138.0, "iron": 4.25, "calcium": 52.0},
            ),  # fmt: skip
        ]

    def search(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.records

    def food(self, fdc_id):
        if self.error:
            raise self.error
        return next(r for r in self.records if r.fdc_id == fdc_id)


@pytest.fixture
def fake_fdc(client):
    fake = FakeFdc()
    client.app.dependency_overrides[get_fdc_client] = lambda: fake
    return fake


def _own(client, name="Płatki owsiane"):
    body = {"name": name, "unit": "g", "per_100": {"kcal": 372}}
    return client.put(f"/api/foods/custom/{uuid.uuid4()}", json=body).json()


def test_fdc_candidates_translate_once_and_rank(logged_in, label_ai, fake_fdc):
    food = _own(logged_in)
    label_ai.outcomes = [{"query_en": "Oats, rolled"}]
    response = logged_in.get(f"/api/foods/{food['id']}/fdc")
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Oats, rolled"
    assert body["suggested_id"] == 2346396
    assert [c["fdc_id"] for c in body["candidates"]] == [2346396, 175028]
    assert body["candidates"][0]["micros_count"] == 3
    assert "Płatki owsiane" in label_ai.calls[0]["prompt"]

    # Tłumaczenie zapamiętane: drugie wyszukiwanie bez wywołania modelu.
    logged_in.get(f"/api/foods/{food['id']}/fdc")
    assert len(label_ai.calls) == 1
    assert fake_fdc.queries == ["Oats, rolled", "Oats, rolled"]
    # Własne zapytanie użytkownika ma pierwszeństwo.
    assert (
        logged_in.get(f"/api/foods/{food['id']}/fdc", params={"q": "oat bran"}).json()["query"]
        == "oat bran"
    )


def test_choosing_fdc_record_saves_reference_micros(logged_in, fake_fdc):
    food = _own(logged_in)
    saved = logged_in.put(f"/api/foods/{food['id']}/fdc", json={"fdc_id": 2346396}).json()
    assert saved["fdc_id"] == 2346396
    assert saved["fdc_description"] == "Oats, whole grain, rolled, old fashioned"
    micros = {m["nutrient_id"]: (m["amount_per_100g"], m["source"]) for m in saved["micros"]}
    # W słowniku testowym są tylko wapń i witamina C: reszta jest pomijana.
    assert micros == {"calcium": (52.0, "reference")}

    entry = logged_in.put(
        f"/api/diary/entries/{uuid.uuid4()}",
        json={"date": "2026-11-18", "meal_slot": "breakfast", "food_id": food["id"], "amount": 50},
    ).json()
    assert entry["values"]["kcal"] == pytest.approx(186)

    removed = logged_in.delete(f"/api/foods/{food['id']}/fdc").json()
    assert (removed["fdc_id"], removed["micros"]) == (None, [])


def test_packaged_product_inherits_estimated_and_keeps_label(logged_in, fake_fdc):
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    saved = logged_in.put(f"/api/foods/{serek['id']}/fdc", json={"fdc_id": 2346396}).json()
    micros = {m["nutrient_id"]: (m["amount_per_100g"], m["source"]) for m in saved["micros"]}
    assert micros == {"calcium": (80.0, "label")}  # etykieta wygrywa z tabelą
    removed = logged_in.delete(f"/api/foods/{serek['id']}/fdc").json()
    assert removed["micros"] == [
        {"nutrient_id": "calcium", "amount_per_100g": 80.0, "source": "label"}
    ]


def test_fdc_errors_are_visible(logged_in, label_ai, fake_fdc):
    food = _own(logged_in)
    fake_fdc.error = FdcRateLimited("limit")
    response = logged_in.get(f"/api/foods/{food['id']}/fdc", params={"q": "oats"})
    assert response.status_code == 429
    assert "FDC_API_KEY" in response.json()["detail"]
    assert logged_in.put(f"/api/foods/{food['id']}/fdc", json={"fdc_id": 1}).status_code == 429
    assert logged_in.get("/api/foods/999/fdc", params={"q": "x"}).status_code == 404


def test_fdc_requires_login(client):
    assert client.get("/api/foods/1/fdc").status_code == 401
    assert client.put("/api/foods/1/fdc", json={"fdc_id": 1}).status_code == 401


# ====================================================================== szacunek AI i tydzień


def test_ai_draft_carries_estimated_micros(logged_in, label_ai):
    from tests.test_ai_meals import estimate, item

    label_ai.outcomes = [estimate(item("banan", grams=120, kcal=89))]
    draft = logged_in.post("/api/ai/meal/text", json={"text": "banan"}).json()
    assert draft["items"][0]["estimate_micros"] == {
        "vit_c": 14.0,
        "potassium": 237.0,
        "magnesium": 11.0,
    }


def test_week_summary_with_sources(logged_in, fake_fdc):
    oats = _own(logged_in)
    logged_in.put(f"/api/foods/{oats['id']}/fdc", json={"fdc_id": 2346396})

    def add(day, **body):
        payload = {"date": day, "meal_slot": "lunch", "amount": 100, **body}
        assert logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=payload).status_code == 200

    add("2026-11-16", food_id=oats["id"])  # 372 kcal, wapń 52 mg z tabeli
    estimate = {"name": "banan", "per_100": {"kcal": 89}, "micros_per_100": {"calcium": 5}}
    add("2026-11-18", estimate=estimate, source="photo")  # 89 kcal, wapń szacowany
    add("2026-11-18", estimate={"name": "kawa", "per_100": {"kcal": 39}}, source="text")
    add("2026-11-10", food_id=oats["id"])  # poza tygodniem

    week = logged_in.get("/api/diary/week/2026-11-18").json()
    assert (week["start"], week["end"], week["logged_days"]) == ("2026-11-12", "2026-11-18", 2)
    assert [d["entries"] for d in week["days"]] == [0, 0, 0, 0, 1, 0, 2]
    assert week["average"]["kcal"] == pytest.approx((372 + 89 + 39) / 2)
    calcium = next(m for m in week["micros"] if m["nutrient_id"] == "calcium")
    assert (calcium["name_pl"], calcium["unit"], calcium["group"]) == ("Wapń", "mg", "mineral")
    assert calcium["avg_amount"] == pytest.approx((52 + 5) / 2)
    assert calcium["percent_rda"] == pytest.approx(28.5 / 800 * 100)
    assert calcium["share_trusted"] == pytest.approx(372 / 500)
    assert calcium["share_estimated"] == pytest.approx(89 / 500)
    assert calcium["share_missing"] == pytest.approx(39 / 500)


def test_week_requires_login(client):
    assert client.get("/api/diary/week/2026-11-18").status_code == 401


def test_nutrient_dictionary(logged_in):
    names = {
        n["id"]: (n["name_pl"], n["unit"], n["group"])
        for n in logged_in.get("/api/foods/nutrients").json()
    }
    assert names["calcium"] == ("Wapń", "mg", "mineral")


def test_fill_missing_micros_only_adds():
    food = {"calcium": (52.0, "reference"), "iron": (4.0, "reference")}
    entry = {"calcium": {"amount": 10.0, "source": "label"}}
    filled = fill_missing_micros(entry, food, amount=50)
    assert filled == {
        "calcium": {"amount": 10.0, "source": "label"},  # istniejąca wartość zostaje
        "iron": {"amount": 2.0, "source": "reference"},
    }
    assert fill_missing_micros(filled, food, 50) is None  # nic do dodania
    assert fill_missing_micros(None, {}, 50) is None


def test_choosing_record_fills_old_entries_without_touching_values(logged_in, fake_fdc):
    """Od 18.11.2026 dopasowanie od razu uzupełnia wpisy (decyzja właściciela)."""
    oats = _own(logged_in)
    entry_id = str(uuid.uuid4())
    body = {"date": "2026-11-16", "meal_slot": "breakfast", "food_id": oats["id"], "amount": 50}
    before = logged_in.put(f"/api/diary/entries/{entry_id}", json=body).json()
    logged_in.put(f"/api/foods/{oats['id']}/fdc", json={"fdc_id": 2346396})
    assert logged_in.post(f"/api/foods/{oats['id']}/micros/backfill").json() == {"updated": 0}
    week = logged_in.get("/api/diary/week/2026-11-18").json()
    calcium = next(m for m in week["micros"] if m["nutrient_id"] == "calcium")
    assert calcium["avg_amount"] == pytest.approx(26)  # 52 mg/100 g × 50 g
    day = logged_in.get("/api/diary/2026-11-16").json()
    assert day["entries"][0]["values"] == before["values"]  # kalorie i makro zamrożone


def test_micro_gaps_rank_products_without_vitamins():
    full = {nid: {"amount": 1.0, "source": "reference"} for nid in ("a", "b", "c", "d", "e")}
    entries = [
        {"food_id": 1, "kcal": 670, "micros": {"sodium": {"amount": 1, "source": "label"}}},
        {"food_id": 2, "kcal": 210, "micros": None},
        {"food_id": 2, "kcal": 100, "micros": {}},
        {"food_id": 3, "kcal": 500, "micros": full},  # ma dane: nie jest brakiem
        {"food_id": None, "kcal": 400, "micros": None},  # stary szacunek AI
    ]
    gaps, orphan = micro_gaps(entries)
    assert [(g.food_id, g.kcal, g.entries) for g in gaps] == [(1, 670, 1), (2, 310, 2)]
    assert gaps[0].share == pytest.approx(670 / 1880)
    assert orphan == pytest.approx(400 / 1880)
    assert micro_gaps(entries, limit=1)[0][0].food_id == 1
    assert micro_gaps([]) == ([], 0)


def test_week_gaps_endpoint_lists_products_and_clears_after_match(logged_in, fake_fdc):
    oats = _own(logged_in)
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    for food_id, amount in ((oats["id"], 100), (serek["id"], 200)):
        body = {"date": "2026-11-18", "meal_slot": "lunch", "food_id": food_id, "amount": amount}
        logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=body)
    est = {"name": "kawa", "per_100": {"kcal": 39}}
    logged_in.put(
        f"/api/diary/entries/{uuid.uuid4()}",
        json={"date": "2026-11-18", "meal_slot": "lunch", "amount": 100, "estimate": est,
              "source": "text"},
    )  # fmt: skip

    gaps = logged_in.get("/api/diary/week/2026-11-18/gaps").json()
    assert [(g["name"], g["has_micros"]) for g in gaps["foods"]] == [
        ("Płatki owsiane", False),  # 372 kcal
        ("Serek wiejski", False),  # 194 kcal, wapń z etykiety to za mało
    ]
    assert gaps["share_without_food"] == pytest.approx(39 / (372 + 194 + 39))

    # Słownik testowy ma tylko 2 składniki, więc „pełne dane" udajemy niższym progiem.
    import app.api.diary as diary_api

    diary_api.MIN_MICROS = 1
    try:
        logged_in.put(f"/api/foods/{oats['id']}/fdc", json={"fdc_id": 2346396})
        gaps = logged_in.get("/api/diary/week/2026-11-18/gaps").json()
        oats_gap = next(g for g in gaps["foods"] if g["food_id"] == oats["id"])
        assert oats_gap["has_micros"] is True  # dopasowany: wystarczy uzupełnić wpisy
    finally:
        diary_api.MIN_MICROS = 5


# ====================================================================== automat (18.11.2026)


def test_auto_match_needs_good_name_and_plausible_kcal():
    candidates = [
        (175028, "Rolls, dinner, oat bran", 236),
        (2346396, "Oats, whole grain, rolled, old fashioned", 379),
        (173576, "Oil, oat", 884),
    ]
    assert auto_match("Oats, rolled", 372, candidates) == 2346396
    assert auto_match("Oats, rolled", None, candidates) == 2346396  # brak kcal produktu
    # Ta sama nazwa, ale kalorie kilkukrotnie inne: to nie ten produkt.
    assert auto_match("Oats, rolled", 40, candidates) is None
    assert auto_match("Pierogi, ruskie", 200, candidates) is None  # słaba ocena nazwy
    assert auto_match("Oats", 372, []) is None


def test_kcal_plausible():
    assert kcal_plausible(21, 42)  # Coca-Cola z mniejszą ilością cukru a zwykła cola
    assert not kcal_plausible(372, 1000)
    assert kcal_plausible(None, 300) and kcal_plausible(100, None)


def _week_autofill(client):
    return client.post("/api/diary/week/2026-11-18/autofill").json()


def test_week_autofill_matches_without_asking(logged_in, label_ai, fake_fdc):
    import app.api.diary as diary_api
    import app.core.week as week_core
    import app.services.micros_fill as fill

    oats = _own(logged_in)
    pierogi = _own(logged_in, "Pierogi ruskie")
    for food_id in (oats["id"], pierogi["id"]):
        body = {"date": "2026-11-18", "meal_slot": "lunch", "food_id": food_id, "amount": 100}
        logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=body)
    label_ai.outcomes = [{"query_en": "Oats, rolled"}, {"query_en": "Dumplings, potato, cheese"}]

    # Słownik testowy ma 2 składniki: próg „pełnych danych" obniżony na czas testu.
    old = fill.MIN_MICROS, diary_api.MIN_MICROS, week_core.MIN_MICROS
    fill.MIN_MICROS = diary_api.MIN_MICROS = week_core.MIN_MICROS = 1
    try:
        result = _week_autofill(logged_in)
        assert result == {
            "filled": ["Płatki owsiane"],
            "completed": [],
            "no_match": ["Pierogi ruskie"],  # brak pewnego rekordu: wybór ręczny
            "postponed": [],
        }
        week = logged_in.get("/api/diary/week/2026-11-18").json()
        calcium = next(m for m in week["micros"] if m["nutrient_id"] == "calcium")
        assert calcium["avg_amount"] == pytest.approx(52)

        # Drugi raz: nic nie jest wyszukiwane ponownie (oszczędza limit USDA i model).
        searches = len(fake_fdc.queries)
        assert _week_autofill(logged_in)["filled"] == []
        assert len(fake_fdc.queries) == searches
        gaps = logged_in.get("/api/diary/week/2026-11-18/gaps").json()["foods"]
        assert [(g["name"], g["checked"]) for g in gaps] == [("Pierogi ruskie", True)]
    finally:
        fill.MIN_MICROS, diary_api.MIN_MICROS, week_core.MIN_MICROS = old


def test_week_autofill_postpones_on_network_errors(logged_in, label_ai, fake_fdc):
    oats = _own(logged_in)
    body = {"date": "2026-11-18", "meal_slot": "lunch", "food_id": oats["id"], "amount": 100}
    logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=body)
    label_ai.outcomes = [{"query_en": "Oats, rolled"}]
    fake_fdc.error = FdcRateLimited("limit")
    assert _week_autofill(logged_in)["postponed"] == ["Płatki owsiane"]
    fake_fdc.error = None
    assert _week_autofill(logged_in)["filled"] == ["Płatki owsiane"]  # następna próba się udaje


def test_removed_match_is_not_redone_automatically(logged_in, fake_fdc):
    oats = _own(logged_in)
    body = {"date": "2026-11-18", "meal_slot": "lunch", "food_id": oats["id"], "amount": 100}
    logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=body)
    logged_in.put(f"/api/foods/{oats['id']}/fdc", json={"fdc_id": 2346396})
    logged_in.delete(f"/api/foods/{oats['id']}/fdc")
    assert _week_autofill(logged_in)["no_match"] == ["Płatki owsiane"]


def test_new_entry_fills_vitamins_in_background(client, settings, label_ai, fake_fdc):
    settings.micros_autofill = True
    assert (
        client.post("/api/auth/login", json={"password": "bardzo-tajne-haslo"}).status_code == 200
    )
    oats = _own(client)
    label_ai.outcomes = [{"query_en": "Oats, rolled"}]
    body = {"date": "2026-11-18", "meal_slot": "lunch", "food_id": oats["id"], "amount": 100}
    entry = client.put(f"/api/diary/entries/{uuid.uuid4()}", json=body).json()
    assert entry["values"]["kcal"] == 372  # odpowiedź nie czeka na USDA
    # TestClient wykonuje zadania w tle przed zwróceniem odpowiedzi.
    food = client.get(f"/api/foods/{oats['id']}").json()
    assert food["fdc_description"] == "Oats, whole grain, rolled, old fashioned"
    day = client.get("/api/diary/2026-11-18").json()
    assert day["entries"][0]["values"] == entry["values"]


def test_background_failure_never_breaks_the_diary(client, settings, label_ai):
    settings.micros_autofill = True  # domyślna atrapa USDA zgłasza brak sieci
    assert (
        client.post("/api/auth/login", json={"password": "bardzo-tajne-haslo"}).status_code == 200
    )
    oats = _own(client)
    label_ai.outcomes = [RuntimeError("cokolwiek")]
    body = {"date": "2026-11-18", "meal_slot": "lunch", "food_id": oats["id"], "amount": 100}
    assert client.put(f"/api/diary/entries/{uuid.uuid4()}", json=body).status_code == 200
