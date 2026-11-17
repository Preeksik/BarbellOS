"""Etap 1, kroki 4–6: cele dzienne, wyszukiwarka z ostatnimi i ulubionymi, zapisane posiłki."""

import uuid
from datetime import date

import httpx
import pytest

from app.core.barcode import is_valid_ean
from app.core.meals import meal_errors, meal_totals
from app.core.search import Candidate, fold, match_score, rank
from app.core.targets import (
    GOAL_KINDS,
    TargetRow,
    active_version,
    goal_errors,
    goals_to_rows,
    rows_to_goals,
)
from app.off.client import RateLimiter, parse_search

EAN = "5900000000015"  # serek z conftest: 97 kcal, B 11 na 100 g
EMPTY_GOALS = dict.fromkeys(GOAL_KINDS)

# ====================================================================== krok 4: cele


def test_goals_round_trip_through_rows_by_kind():
    goals = {**EMPTY_GOALS, "kcal": 2800, "protein_g": 180, "salt_g": 5}
    rows = {row.nutrient_id: row for row in goals_to_rows(goals)}
    assert len(rows) == 8  # komplet: także składniki bez celu
    assert (rows["kcal"].low, rows["kcal"].high) == (2800, 2800)  # cel
    assert (rows["protein_g"].low, rows["protein_g"].high) == (180, None)  # co najmniej
    assert (rows["salt_g"].low, rows["salt_g"].high) == (None, 5)  # najwyżej
    assert (rows["fiber_g"].low, rows["fiber_g"].high) == (None, None)  # bez celu
    assert rows_to_goals(rows.values()) == goals


def test_rows_to_goals_ignores_micros_and_missing_rows():
    goals = rows_to_goals([TargetRow("kcal", 2500, 2500), TargetRow("magnesium", 400, None)])
    assert goals["kcal"] == 2500
    assert goals["protein_g"] is None
    assert "magnesium" not in goals


def test_active_version_is_latest_not_after_the_day():
    versions = [date(2026, 11, 1), date(2026, 11, 10)]
    assert active_version(versions, date(2026, 10, 31)) is None
    assert active_version(versions, date(2026, 11, 1)) == date(2026, 11, 1)
    assert active_version(versions, date(2026, 11, 9)) == date(2026, 11, 1)
    assert active_version(versions, date(2026, 12, 24)) == date(2026, 11, 10)
    assert active_version([], date(2026, 11, 1)) is None


@pytest.mark.parametrize(
    ("goals", "fragment"),
    [
        ({"kcal": 25000}, "Energia: cel 25000 jest poza zakresem"),
        ({"protein_g": 0}, "Białko: cel 0"),
        ({"salt_g": -1}, "Sól: cel -1"),
        ({"magnesium": 400}, "Nieznany składnik: magnesium"),
    ],
)
def test_goal_errors(goals, fragment):
    assert any(fragment in error for error in goal_errors(goals))


def test_goal_errors_accept_empty_and_sensible_goals():
    assert goal_errors(EMPTY_GOALS) == []
    assert goal_errors({**EMPTY_GOALS, "kcal": 2800, "fiber_g": 30, "salt_g": 5}) == []


def _put_goals(client, date_from: str, **goals):
    return client.put(f"/api/targets/{date_from}", json={"goals": {**EMPTY_GOALS, **goals}})


def test_targets_require_login(client):
    assert client.get("/api/targets/2026-11-17").status_code == 401
    assert _put_goals(client, "2026-11-17", kcal=2800).status_code == 401


def test_no_targets_yet(logged_in):
    body = logged_in.get("/api/targets/2026-11-17").json()
    assert body["date_from"] is None
    assert body["goals"] == EMPTY_GOALS
    assert body["kinds"]["protein_g"] == "min"


def test_changing_goals_keeps_history(logged_in):
    first = _put_goals(logged_in, "2026-11-10", kcal=3000, protein_g=180)
    assert first.status_code == 200
    assert first.json()["goals"]["kcal"] == 3000
    _put_goals(logged_in, "2026-11-17", kcal=2600, protein_g=190, salt_g=5)

    before = logged_in.get("/api/targets/2026-11-12").json()
    assert (before["date_from"], before["goals"]["kcal"], before["goals"]["salt_g"]) == (
        "2026-11-10",
        3000,
        None,
    )
    after = logged_in.get("/api/targets/2026-11-20").json()
    assert (after["date_from"], after["goals"]["kcal"], after["goals"]["salt_g"]) == (
        "2026-11-17",
        2600,
        5,
    )
    assert logged_in.get("/api/targets/2026-11-01").json()["date_from"] is None


def test_putting_goals_again_is_idempotent_and_can_clear_a_goal(logged_in):
    _put_goals(logged_in, "2026-11-10", kcal=3000, protein_g=180)
    _put_goals(logged_in, "2026-11-17", kcal=2600, protein_g=180)
    again = _put_goals(logged_in, "2026-11-17", kcal=2600).json()
    # Białko usunięte od 17.11 nie wraca z wersji z 10.11.
    assert again["goals"]["protein_g"] is None
    assert logged_in.get("/api/targets/2026-11-12").json()["goals"]["protein_g"] == 180


def test_impossible_goals_are_rejected(logged_in):
    response = _put_goals(logged_in, "2026-11-17", kcal=25000)
    assert response.status_code == 422
    assert "poza zakresem" in response.json()["detail"]
    assert logged_in.get("/api/targets/2026-11-17").json()["date_from"] is None


# ====================================================================== krok 5: wyszukiwanie


def test_fold_removes_polish_letters():
    assert fold("Śmietanka ŁACIATA 30% Żółć") == "smietanka laciata 30% zolc"


@pytest.mark.parametrize(
    ("query", "name", "brand", "matches"),
    [
        ("ser wiej", "Serek wiejski", None, True),
        ("SEREK", "serek wiejski", None, True),
        ("smietanka", "Śmietanka 30%", None, True),
        ("łaciata", "Mleko", "Łaciate", False),  # „laciata" nie jest początkiem „laciate"
        ("laciat", "Mleko", "Łaciate", True),  # marka też się liczy
        ("ser", "Deser czekoladowy", None, False),  # tylko początek słowa
        ("mleko owsiane", "Mleko krowie", None, False),  # każde słowo musi pasować
        ("s", "Serek", None, False),  # za krótkie
        ("  ", "Serek", None, False),
    ],
)
def test_match_score(query, name, brand, matches):
    assert (match_score(query, Candidate(1, name, brand)) is not None) is matches


def test_rank_prefers_whole_words_start_of_name_favorites_and_history():
    foods = [
        Candidate(1, "Jogurt naturalny", "Piątnica"),
        Candidate(2, "Napój jogurtowy", None),
        Candidate(3, "Jogurt naturalny", "Bakoma", uses=12),
        Candidate(4, "Jogurt grecki", None, favorite=True),
        Candidate(5, "Masło", None),
    ]
    assert rank("jogurt", foods) == [3, 4, 1, 2]
    assert rank("jogurt", foods, limit=2) == [3, 4]
    assert rank("piątnica", foods) == [1]
    assert rank("xyz", foods) == []


def _own_product(client, name: str, brand: str | None = None, **per_100) -> dict:
    body = {
        "name": name,
        "brand": brand,
        "unit": "g",
        "per_100": {"kcal": 100, **per_100},
    }
    response = client.put(f"/api/foods/custom/{uuid.uuid4()}", json=body)
    assert response.status_code == 200
    return response.json()


def test_search_own_database(logged_in):
    logged_in.get(f"/api/foods/barcode/{EAN}")  # „Serek wiejski" trafia do bazy
    _own_product(logged_in, "Owsianka domowa")
    found = logged_in.get("/api/foods/search", params={"q": "serek"}).json()["foods"]
    assert [food["name"] for food in found] == ["Serek wiejski"]
    assert found[0]["per_100"]["kcal"] == 97  # pełny produkt: da się go dodać bez sieci
    assert logged_in.get("/api/foods/search", params={"q": "o"}).json()["foods"] == []
    assert logged_in.get("/api/foods/search").status_code == 422


def test_search_requires_login(client):
    assert client.get("/api/foods/search", params={"q": "ser"}).status_code == 401
    assert client.get("/api/foods/search/off", params={"q": "ser"}).status_code == 401
    assert client.get("/api/foods/recent").status_code == 401


OFF_SEARCH_PAYLOAD = {
    "hits": [
        {
            "code": "5900531000423",
            "product_name": "Jogurt Naturalny",
            "brands": ["Piątnica"],
            "quantity": "180g",
            "nutriments": {"energy-kcal_100g": 58},
        },
        {
            "code": "4006381333931",
            "product_name": "Kefir",
            "product_name_pl": "Kefir naturalny",
            "brands": "Testowa, Inna",
            "quantity": "1 l",
            "nutriments": {"energy_100g": 209.2},
        },
        {"code": "123", "product_name": "Zły kod"},
        {"code": "96385074", "product_name": "", "brands": None},
    ]
}


def test_parse_search_keeps_only_usable_hits():
    hits = parse_search(OFF_SEARCH_PAYLOAD, is_valid_ean)
    assert [(h.barcode, h.name, h.brand, h.unit) for h in hits] == [
        ("5900531000423", "Jogurt Naturalny", "Piątnica", "g"),
        ("4006381333931", "Kefir naturalny", "Testowa", "ml"),
    ]
    assert hits[0].kcal == 58
    assert hits[1].kcal == pytest.approx(50)  # z kJ
    assert parse_search({}, is_valid_ean) == []


def test_search_off_returns_hits_without_saving_them(logged_in, off_search, off_calls):
    off_search.payload = OFF_SEARCH_PAYLOAD
    response = logged_in.get("/api/foods/search/off", params={"q": " jogurt naturalny "})
    assert response.status_code == 200
    assert [hit["barcode"] for hit in response.json()] == ["5900531000423", "4006381333931"]
    assert off_search.queries == ["jogurt naturalny"]
    # Wynik z OFF nie jest jeszcze produktem: zapisuje się po wybraniu, przez kod kreskowy.
    assert logged_in.get("/api/foods/search", params={"q": "jogurt"}).json()["foods"] == []
    assert off_calls == []


def test_search_off_failures(logged_in, off_search):
    off_search.error = httpx.ConnectTimeout("brak sieci")
    response = logged_in.get("/api/foods/search/off", params={"q": "kefir"})
    assert response.status_code == 502
    assert logged_in.get("/api/foods/search/off", params={"q": "k"}).status_code == 422


def test_search_off_is_rate_limited_before_off_bans_the_server(logged_in, off_search):
    statuses = [
        logged_in.get("/api/foods/search/off", params={"q": f"jogurt {i}"}).status_code
        for i in range(10)
    ]
    assert statuses == [200] * 8 + [429, 429]
    assert len(off_search.queries) == 8  # zablokowane zapytania nie wychodzą do OFF


def test_rate_limiter_window():
    limiter = RateLimiter(limit=2, window_s=60)
    assert limiter.allow(0) and limiter.allow(10)
    assert not limiter.allow(30)
    assert limiter.allow(61)  # pierwsze zdarzenie wypadło z okna


def _add(client, food_id: int, amount: float, slot="breakfast", day="2026-11-17") -> dict:
    body = {"date": day, "meal_slot": slot, "food_id": food_id, "amount": amount}
    response = client.put(f"/api/diary/entries/{uuid.uuid4()}", json=body)
    assert response.status_code == 200
    return response.json()


def test_recent_lists_each_food_once_with_last_amount(logged_in):
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    owsianka = _own_product(logged_in, "Owsianka")
    _add(logged_in, serek["id"], 150)
    _add(logged_in, owsianka["id"], 300, slot="breakfast")
    _add(logged_in, serek["id"], 200, slot="dinner")

    recent = logged_in.get("/api/foods/recent").json()
    assert [(r["food"]["name"], r["last_amount"], r["last_slot"]) for r in recent] == [
        ("Serek wiejski", 200, "dinner"),
        ("Owsianka", 300, "breakfast"),
    ]


def test_favorites(logged_in):
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    assert serek["favorite"] is False
    assert logged_in.get("/api/foods/favorites").json() == []

    on = logged_in.put(f"/api/foods/{serek['id']}/favorite", json={"favorite": True})
    assert on.status_code == 200 and on.json()["favorite"] is True
    again = logged_in.put(f"/api/foods/{serek['id']}/favorite", json={"favorite": True})
    assert again.json()["favorite"] is True  # idempotentne
    assert [f["id"] for f in logged_in.get("/api/foods/favorites").json()] == [serek["id"]]
    assert logged_in.get(f"/api/foods/barcode/{EAN}").json()["favorite"] is True

    logged_in.put(f"/api/foods/{serek['id']}/favorite", json={"favorite": False})
    assert logged_in.get("/api/foods/favorites").json() == []
    assert logged_in.put("/api/foods/999/favorite", json={"favorite": True}).status_code == 404


def test_custom_product_without_barcode(logged_in):
    client_id = str(uuid.uuid4())
    body = {
        "name": "Leczo domowe",
        "unit": "g",
        "per_100": {"kcal": 85, "protein_g": 4, "fat_g": 5, "carbs_g": 6, "fiber_g": None},
    }
    first = logged_in.put(f"/api/foods/custom/{client_id}", json=body).json()
    assert (first["barcode"], first["origin"], first["macro_source"]) == (None, "user", "user")
    assert first["verified_at"] is not None
    assert first["per_100"]["fiber_g"] is None

    # Powtórka z kolejki offline poprawia ten sam produkt.
    second = logged_in.put(
        f"/api/foods/custom/{client_id}", json={**body, "per_100": {**body["per_100"], "kcal": 90}}
    ).json()
    assert second["id"] == first["id"]
    assert second["per_100"]["kcal"] == 90

    assert logged_in.get(f"/api/foods/{first['id']}").json()["name"] == "Leczo domowe"
    assert logged_in.get("/api/foods/999").status_code == 404
    entry = _add(logged_in, first["id"], 250)
    assert entry["values"]["kcal"] == pytest.approx(225)


def test_custom_product_rejects_impossible_values(logged_in):
    body = {"name": "Coś", "unit": "g", "per_100": {"fat_g": 5, "sat_fat_g": 9}}
    response = logged_in.put(f"/api/foods/custom/{uuid.uuid4()}", json=body)
    assert response.status_code == 422
    assert logged_in.get("/api/foods/search", params={"q": "coś"}).json()["foods"] == []


# ====================================================================== krok 6: posiłki


def test_meal_errors():
    assert meal_errors("Śniadanie", [(1, 100)]) == []
    assert "Nazwa posiłku nie może być pusta." in meal_errors("  ", [(1, 100)])
    assert "Posiłek musi mieć co najmniej jeden produkt." in meal_errors("X", [])
    assert any("najwyżej 30 produktów" in e for e in meal_errors("X", [(1, 1)] * 31))
    assert any("Ilość produktu" in e for e in meal_errors("X", [(1, 0)]))
    assert any("najwyżej 120 znaków" in e for e in meal_errors("x" * 121, [(1, 1)]))


def test_meal_totals_keep_missing_values_as_zero_in_sum():
    totals = meal_totals([({"kcal": 97, "fiber_g": None}, 200), ({"kcal": 380}, 50)])
    assert totals["kcal"] == pytest.approx(194 + 190)
    assert totals["fiber_g"] == 0


def _put_meal(client, meal_id: str, name: str, items: list[tuple[int, float]]):
    body = {"name": name, "items": [{"food_id": f, "amount": a} for f, a in items]}
    return client.put(f"/api/meals/{meal_id}", json=body)


def test_meal_lifecycle(logged_in):
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    owsianka = _own_product(logged_in, "Owsianka", protein_g=12)
    meal_id = str(uuid.uuid4())

    assert logged_in.get("/api/meals").json() == []
    response = _put_meal(logged_in, meal_id, "  Śniadanie standard ", [(owsianka["id"], 300)])
    assert response.status_code == 204
    # Powtórka zastępuje skład (idempotentne): zestaw jest jeden.
    _put_meal(logged_in, meal_id, "Śniadanie standard", [(owsianka["id"], 300), (serek["id"], 200)])

    (meal,) = logged_in.get("/api/meals").json()
    assert meal["id"] == meal_id
    assert meal["name"] == "Śniadanie standard"
    assert [(i["food_name"], i["amount"], i["unit"]) for i in meal["items"]] == [
        ("Owsianka", 300, "g"),
        ("Serek wiejski", 200, "g"),
    ]
    assert meal["items"][1]["per_100"]["kcal"] == 97
    assert meal["totals"]["kcal"] == pytest.approx(300 + 194)
    assert meal["totals"]["protein_g"] == pytest.approx(36 + 22)

    assert logged_in.delete(f"/api/meals/{meal_id}").status_code == 204
    assert logged_in.delete(f"/api/meals/{meal_id}").status_code == 204  # idempotentne
    assert logged_in.get("/api/meals").json() == []


def test_meal_rejects_bad_input(logged_in):
    response = _put_meal(logged_in, str(uuid.uuid4()), "X", [(999, 100)])
    assert response.status_code == 404
    assert "999" in response.json()["detail"]
    assert _put_meal(logged_in, str(uuid.uuid4()), "", []).status_code == 422
    assert logged_in.get("/api/meals").json() == []


def test_meal_requires_login(client):
    assert client.get("/api/meals").status_code == 401
    assert _put_meal(client, str(uuid.uuid4()), "X", [(1, 1)]).status_code == 401


def test_meal_added_to_day_is_frozen_like_single_entries(logged_in):
    """Dodanie posiłku to wpisy dziennika: poprawka produktu potem nie zmienia dnia."""
    owsianka = _own_product(logged_in, "Owsianka")
    meal_id = str(uuid.uuid4())
    _put_meal(logged_in, meal_id, "Śniadanie", [(owsianka["id"], 300)])
    (meal,) = logged_in.get("/api/meals").json()

    body = {
        "date": "2026-11-17",
        "meal_slot": "breakfast",
        "food_id": meal["items"][0]["food_id"],
        "amount": meal["items"][0]["amount"],
        "source": "meal",
    }
    entry = logged_in.put(f"/api/diary/entries/{uuid.uuid4()}", json=body).json()
    assert (entry["source"], entry["values"]["kcal"]) == ("meal", 300)

    logged_in.put(
        f"/api/foods/{owsianka['id']}",
        json={"name": "Owsianka", "unit": "g", "per_100": {"kcal": 150}},
    )
    day = logged_in.get("/api/diary/2026-11-17").json()
    assert day["totals"]["kcal"] == 300
    assert logged_in.get("/api/meals").json()[0]["totals"]["kcal"] == 450  # zestaw: na dziś
