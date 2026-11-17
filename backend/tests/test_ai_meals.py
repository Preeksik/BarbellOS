"""Etap 2: szkic posiłku ze zdjęcia i opisu, dopasowanie do bazy, wpisy z szacunkiem, koszty."""

import uuid

import pytest
from sqlalchemy import select

from app.ai.meal_prompts import MEAL_PHOTO_PROMPT, MEAL_TEXT_PROMPT, with_description
from app.ai.provider import AiResult, InvalidResponse, Overloaded, RateLimited, Tier
from app.ai.router import AiRouter, AllProvidersFailed, Task
from app.ai.schemas import MealEstimate
from app.core.ai_cost import call_cost, usage_summary
from app.core.meal_draft import clean_item, clean_items, match_item, match_score
from app.core.search import Candidate
from app.db.models import AiRun

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
EAN = "5900000000015"  # serek wiejski z conftest: 97 kcal na 100 g


def item(name, name_en="", grams=150, low=None, high=None, kcal=100.0, **extra) -> dict:
    return {
        "name_pl": name,
        "name_en": name_en,
        "category": "other",
        "grams": grams,
        "grams_low": grams * 0.8 if low is None else low,
        "grams_high": grams * 1.3 if high is None else high,
        "per_100g_estimate": {"kcal": kcal, "protein_g": 5.0, "fat_g": 2.0, "carbs_g": 15.0},
        "confidence": "medium",
        **extra,
    }


def estimate(*items, notes=None) -> dict:
    return {"items": list(items), "notes": notes}


# ====================================================================== dopasowanie


@pytest.mark.parametrize(
    ("item_name", "food_name", "expected"),
    [
        ("serek wiejski", "Serek wiejski", True),
        ("ryżu białego", "Ryż biały", True),  # odmiana: porównujemy rdzenie słów
        ("pierś z kurczaka pieczona", "Pierś z kurczaka", True),
        ("jogurt naturalny", "Mleko 2%", False),
        ("banan", "Baton bananowy", False),  # baton to nie banan: tylko do wyboru
        ("ser żółty", "Serek wiejski", False),
        ("ser", "Deser czekoladowy", False),
    ],
)
def test_match_item_threshold(item_name, food_name, expected):
    matching = match_item(item_name, "", [Candidate(1, food_name, None)])
    assert (matching.food_id == 1) is expected


def test_close_but_uncertain_product_is_offered_not_chosen():
    matching = match_item("banan", "banana", [Candidate(1, "Baton bananowy", None)])
    assert matching.food_id is None
    assert matching.candidates == [1]


def test_match_prefers_closest_name_and_lists_candidates():
    foods = [
        Candidate(1, "Jogurt naturalny z truskawkami i musli", None),
        Candidate(2, "Jogurt naturalny", "Piątnica"),
        Candidate(3, "Jogurt grecki", None),
        Candidate(4, "Masło", None),
    ]
    matching = match_item("jogurt naturalny", "natural yogurt", foods)
    assert matching.food_id == 2
    assert matching.candidates[0] == 2
    assert 4 not in matching.candidates
    assert set(matching.candidates) >= {1, 3}  # „jogurt" pasuje w połowie: do wyboru


def test_match_uses_english_name_too():
    food = Candidate(1, "Chicken breast", None)
    assert match_score("pierś z kurczaka", "chicken breast", food) >= 0.85


def test_no_match_without_common_words():
    matching = match_item("kawa z mlekiem", "coffee with milk", [Candidate(1, "Herbata", None)])
    assert matching == match_item("kawa z mlekiem", "", [])
    assert matching.food_id is None and matching.candidates == []


# ====================================================================== porządkowanie odczytu


def test_clean_item_keeps_estimate_and_marks_missing_values():
    cleaned = clean_item(item("ryż biały gotowany", grams=200, low=150, high=260, kcal=130))
    assert (cleaned.grams, cleaned.grams_low, cleaned.grams_high) == (200, 150, 260)
    assert cleaned.estimate_per_100["kcal"] == 130
    # Model nie szacuje soli, cukrów itd.: brak danych, nie zero.
    assert cleaned.estimate_per_100["salt_g"] is None
    assert cleaned.estimate_per_100["fiber_g"] is None


def test_clean_item_fixes_impossible_values():
    weird = clean_item(item("zupa", grams=5000, low=9000, high=10, kcal=2500))
    assert weird.grams == 2000
    assert weird.grams_low == 2000 and weird.grams_high == 2000  # zakres poprawiony
    assert weird.estimate_per_100["kcal"] is None  # 2500 kcal na 100 g nie istnieje
    assert "za dużo na jeden posiłek" in weird.warnings[0]
    assert clean_item(item("", grams=100)) is None
    assert clean_item(item("chleb", grams=0)) is None
    assert clean_item({**item("chleb"), "grams": "dużo"}) is None


def test_clean_items_limits_and_reports_skipped():
    items, warnings = clean_items([item(f"składnik {i}") for i in range(20)] + [item("")])
    assert len(items) == 15
    assert any("pierwsze 15" in w for w in warnings)
    _, warnings = clean_items([item("a b"), item("", grams=10)])
    assert warnings == ["Pominięto składniki bez nazwy albo ilości: 1."]


def test_prompts_forbid_arithmetic_and_keep_user_text_as_data():
    for prompt in (MEAL_PHOTO_PROMPT, MEAL_TEXT_PROMPT):
        assert "Nie sumuj kalorii" in prompt
        assert "Nie przeliczaj ich na porcję" in prompt
    assert with_description(MEAL_TEXT_PROMPT, "  ") == MEAL_TEXT_PROMPT
    assert with_description(MEAL_TEXT_PROMPT, "2 jajka").endswith("«2 jajka»\n")


# ====================================================================== koszty


def test_call_cost_from_price_list():
    # 449 tokenów wejścia i 760 wyjścia na Flash-Lite (0,30 / 2,50 USD za milion).
    assert call_cost("gemini-3.5-flash-lite", 449, 760) == pytest.approx(0.0020347)
    assert call_cost("nieznany-model", 100, 100) is None
    assert call_cost("gemini-3.8-flash", None, 10) is None


def test_usage_summary_groups_by_task():
    runs = [
        {"task": "meal_photo", "status": "ok", "input_tokens": 2000, "output_tokens": 600,
         "cost_usd": 0.00375},
        {"task": "meal_photo", "status": "rate_limited", "input_tokens": None,
         "output_tokens": None, "cost_usd": None},
        {"task": "text_to_items", "status": "ok", "input_tokens": 500, "output_tokens": 700,
         "cost_usd": None},
    ]  # fmt: skip
    summary, unpriced = usage_summary(runs)
    photo, text = summary
    assert (photo.task, photo.runs, photo.failed, photo.input_tokens) == ("meal_photo", 2, 1, 2000)
    assert photo.cost_usd == pytest.approx(0.00375)
    assert (text.runs, text.cost_usd) == (1, 0)
    assert unpriced == 1  # nieudane wywołania bez tokenów się nie liczą


# ====================================================================== router: przeciążenie


class Flaky:
    name = "gemini"

    def __init__(self, failures):
        self.failures, self.calls = list(failures), 0

    def supports(self, tier):
        return True

    def generate(self, tier, prompt, schema, images=None):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return AiResult(data=schema.model_validate(estimate(item("a b"))), provider="gemini",
                        model="m")  # fmt: skip


def test_router_retries_once_after_overload():
    waits = []
    provider = Flaky([Overloaded("HTTP 503")])
    result = AiRouter({"gemini": provider}, sleep=waits.append).run(
        Task.MEAL_PHOTO, "p", MealEstimate
    )
    assert result.provider == "gemini"
    assert provider.calls == 2 and waits == [3.0]


def test_router_gives_up_after_second_overload():
    # Dwie próby na model (ponowienie po przeciążeniu), dwa modele Gemini.
    provider = Flaky([Overloaded(str(i)) for i in range(4)])
    with pytest.raises(AllProvidersFailed):
        AiRouter({"gemini": provider}, sleep=lambda _: None).run(Task.MEAL_PHOTO, "p", MealEstimate)
    assert provider.calls == 4


def test_router_uses_the_other_model_when_one_stays_overloaded():
    provider = Flaky([Overloaded("1"), Overloaded("2")])
    result = AiRouter({"gemini": provider}, sleep=lambda _: None).run(
        Task.MEAL_PHOTO, "p", MealEstimate
    )
    assert result.provider == "gemini" and provider.calls == 3


# ====================================================================== API: szkic


def _photo(client, data=JPEG, description=None):
    params = {"description": description} if description else None
    return client.post(
        "/api/ai/meal/photo", content=data, params=params, headers={"Content-Type": "image/jpeg"}
    )


def test_ai_requires_login(client, label_ai):
    assert _photo(client).status_code == 401
    assert client.post("/api/ai/meal/text", json={"text": "2 jajka"}).status_code == 401
    assert client.get("/api/ai/usage").status_code == 401
    assert label_ai.calls == []


def test_photo_draft_matches_own_products_and_keeps_estimates(logged_in, label_ai, db_factory):
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    label_ai.outcomes = [
        estimate(
            item("serek wiejski", "cottage cheese", grams=200, kcal=100),
            item("pomidor", "tomato", grams=120, kcal=18),
            notes="Nie widać, czy serek jest light.",
        )
    ]
    response = _photo(logged_in, description="kolacja po treningu")
    assert response.status_code == 200
    draft = response.json()
    assert draft["source"] == "photo"
    assert draft["notes"] == "Nie widać, czy serek jest light."

    cheese, tomato = draft["items"]
    assert cheese["match"]["id"] == serek["id"]
    # Wartości z produktu z bazy (97 kcal/100 g), nie z szacunku modelu (100).
    assert cheese["values"]["kcal"] == pytest.approx(194)
    assert tomato["match"] is None
    assert tomato["values"]["kcal"] == pytest.approx(21.6)  # szacunek: 18 × 1,2
    assert tomato["values"]["salt_g"] is None
    assert (tomato["grams_low"], tomato["grams_high"]) == (96, 156)

    (call,) = label_ai.calls
    assert call["tier"] == Tier.MID  # zdjęcie posiłku: średni model
    assert call["images"] == [JPEG]
    assert "«kolacja po treningu»" in call["prompt"]

    with db_factory() as db:
        (run,) = db.scalars(select(AiRun)).all()
    assert (run.task, run.status, run.id) == ("meal_photo", "ok", draft["ai_run_id"])
    assert run.cost_usd is None  # „gemini-test" nie ma w cenniku
    # Szkic niczego nie dodaje do dziennika.
    assert logged_in.get("/api/diary/2026-11-17").json()["entries"] == []


def test_text_draft_uses_cheap_model(logged_in, label_ai):
    label_ai.outcomes = [estimate(item("jajko sadzone", "fried egg", grams=100, kcal=196))]
    response = logged_in.post("/api/ai/meal/text", json={"text": "2 jajka sadzone"})
    assert response.status_code == 200
    assert response.json()["source"] == "text"
    assert label_ai.calls[0]["tier"] == Tier.CHEAP
    assert label_ai.calls[0]["images"] is None
    assert "«2 jajka sadzone»" in label_ai.calls[0]["prompt"]


def test_draft_without_food(logged_in, label_ai):
    label_ai.outcomes = [estimate()]
    response = _photo(logged_in)
    assert response.status_code == 422
    assert "Nie rozpoznano jedzenia" in response.json()["detail"]


def test_draft_input_validation(logged_in, label_ai):
    assert _photo(logged_in, data=b"%PDF").status_code == 415
    assert logged_in.post("/api/ai/meal/text", json={"text": "x"}).status_code == 422
    assert label_ai.calls == []


@pytest.mark.parametrize(
    ("outcomes", "status", "fragment"),
    [
        ([RateLimited()] * 2, 429, "limit modelu"),
        ([InvalidResponse("x")] * 4, 502, "nie rozpoznał posiłku"),
        ([Overloaded("x")] * 4, 502, "nie odpowiada"),
    ],
)
def test_draft_failures_are_visible(logged_in, label_ai, outcomes, status, fragment):
    label_ai.outcomes = outcomes
    response = logged_in.post("/api/ai/meal/text", json={"text": "obiad"})
    assert response.status_code == status
    assert fragment in response.json()["detail"]


def test_draft_overload_is_retried(logged_in, label_ai):
    label_ai.outcomes = [Overloaded("503"), estimate(item("zupa pomidorowa", grams=300))]
    assert logged_in.post("/api/ai/meal/text", json={"text": "zupa"}).status_code == 200


# ====================================================================== wpisy z szacunkiem


def _entry(client, entry_id=None, **body):
    base = {"date": "2026-11-17", "meal_slot": "lunch", "amount": 120}
    return client.put(f"/api/diary/entries/{entry_id or uuid.uuid4()}", json={**base, **body})


ESTIMATE = {
    "name": "pomidor",
    "per_100": {"kcal": 18, "protein_g": 0.9, "fat_g": 0.2, "carbs_g": 3.9},
}


def test_estimated_entry_is_frozen_and_marked(logged_in, label_ai):
    label_ai.outcomes = [estimate(item("pomidor", grams=120, kcal=18))]
    run_id = logged_in.post("/api/ai/meal/text", json={"text": "pomidor"}).json()["ai_run_id"]
    entry_id = str(uuid.uuid4())
    response = _entry(logged_in, entry_id, estimate=ESTIMATE, source="photo", ai_run_id=run_id)
    assert response.status_code == 200
    saved = response.json()
    assert (saved["food_id"], saved["food_name"], saved["unit"]) == (None, "pomidor", "g")
    assert saved["macro_source"] == "estimated"
    assert saved["ai_run_id"] == run_id
    assert saved["values"]["kcal"] == pytest.approx(21.6)
    assert saved["values"]["salt_g"] is None

    # Zmiana ilości w dzienniku: bez ponownego szacunku, wartości skalowane.
    edited = _entry(logged_in, entry_id, amount=240, source="photo").json()
    assert edited["values"]["kcal"] == pytest.approx(43.2)
    assert edited["macro_source"] == "estimated"
    assert edited["ai_run_id"] == run_id


def test_estimate_only_for_ai_entries(logged_in):
    assert _entry(logged_in, estimate=ESTIMATE, source="scan").status_code == 422
    assert _entry(logged_in, source="photo").status_code == 422  # brak szacunku
    impossible = {**ESTIMATE, "per_100": {"kcal": 1500}}
    assert _entry(logged_in, estimate=impossible, source="text").status_code == 422


def test_unknown_ai_run_is_not_linked(logged_in):
    saved = _entry(logged_in, estimate=ESTIMATE, source="text", ai_run_id=999).json()
    assert saved["ai_run_id"] is None


def test_product_entries_carry_the_product_source(logged_in):
    serek = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    saved = _entry(logged_in, food_id=serek["id"], source="photo").json()
    assert saved["macro_source"] == "label"


# ====================================================================== API: koszty


def test_usage_for_month(logged_in, label_ai, db_factory):
    from datetime import UTC, datetime

    label_ai.outcomes = [estimate(item("zupa", grams=300))]
    logged_in.post("/api/ai/meal/text", json={"text": "zupa"})
    with db_factory() as db:
        db.add(
            AiRun(
                task="meal_photo",
                provider="gemini",
                model="gemini-3.8-flash",
                status="ok",
                input_tokens=2000,
                output_tokens=600,
                cost_usd=call_cost("gemini-3.8-flash", 2000, 600),
                created_at=datetime(2026, 10, 5, 12, tzinfo=UTC),
            )  # fmt: skip
        )
        db.commit()

    october = logged_in.get("/api/ai/usage", params={"month": "2026-10"}).json()
    assert october["runs"] == 1
    assert october["cost_usd"] == pytest.approx(0.00375)  # 2000 × 0,75 + 600 × 3,75 (za mln)
    assert october["by_task"][0]["task"] == "meal_photo"

    current = logged_in.get("/api/ai/usage").json()
    assert current["runs"] == 1
    assert current["unpriced_runs"] == 1  # model testowy spoza cennika
    assert logged_in.get("/api/ai/usage", params={"month": "2026-13"}).status_code == 422
