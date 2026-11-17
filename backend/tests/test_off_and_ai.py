import pytest
from pydantic import BaseModel

from app.ai.provider import AiResult, RateLimited, Tier
from app.ai.router import AiRouter, AllProvidersFailed, Task
from app.ai.schemas import MealEstimate
from app.off.client import parse_product

# Odpowiedź w kształcie API Open Food Facts v2. Dane syntetyczne, nie prawdziwy produkt.
OFF_PAYLOAD = {
    "code": "5900000000015",
    "status": 1,
    "product": {
        "product_name": "Cottage cheese",
        "product_name_pl": "Serek wiejski",
        "brands": "Testowa, Inna",
        "serving_quantity": "200",
        "categories_tags": ["en:dairies", "en:cheeses", "en:cottage-cheeses"],
        "nutriments": {
            "energy-kcal_100g": 97,
            "proteins_100g": 11,
            "fat_100g": 5,
            "saturated-fat_100g": 3.5,
            "carbohydrates_100g": 2,
            "sugars_100g": 2,
            "salt_100g": 0.7,
            "sodium_100g": 0.28,
            "calcium_100g": 0.08,
            "vitamin-b12_100g": 0.0000004,
        },
    },
}


def test_parse_product_maps_label_values():
    draft = parse_product(OFF_PAYLOAD)
    assert draft.name == "Serek wiejski"
    assert draft.brand == "Testowa"
    assert draft.category == "en:cottage-cheeses"
    assert draft.serving_g == 200
    assert draft.macros["sat_fat_g"] == 3.5
    assert draft.macros["fiber_g"] is None  # brak na etykiecie to brak, nie zero


def test_parse_product_converts_micros_from_grams():
    micros = parse_product(OFF_PAYLOAD).micros
    assert micros["calcium"] == pytest.approx(80)  # mg
    assert micros["vit_b12"] == pytest.approx(0.4)  # µg
    assert micros["sodium"] == pytest.approx(280)  # mg
    assert "iron" not in micros


def test_parse_product_fallbacks():
    payload = {
        "code": "1",
        "status": 1,
        "product": {"nutriments": {"energy_100g": 418.4, "sodium_100g": 0.4}},
    }
    draft = parse_product(payload)
    assert draft.macros["kcal"] == pytest.approx(100)  # z kJ
    assert draft.macros["salt_g"] == pytest.approx(1.0)  # z sodu
    assert draft.name == "(bez nazwy)"


def test_parse_product_detects_drinks_and_source_date():
    from datetime import UTC, datetime

    def product(**fields):
        return parse_product({"code": "1", "status": 1, "product": {"nutriments": {}, **fields}})

    assert parse_product(OFF_PAYLOAD).unit == "g"
    assert parse_product(OFF_PAYLOAD).source_updated_at is None
    assert product(quantity="330 ml").unit == "ml"
    assert product(quantity="1,5 L").unit == "ml"
    assert product(quantity="6 x 0.33l").unit == "ml"
    assert product(quantity="250 g").unit == "g"
    assert product(quantity="500 ml", product_quantity_unit="g").unit == "g"
    assert product(product_quantity_unit="ml").unit == "ml"
    assert product(quantity="mleko 2 szt.").unit == "g"
    dated = product(last_modified_t=1616000000)
    assert dated.source_updated_at == datetime(2021, 3, 17, 16, 53, 20, tzinfo=UTC)


def test_parse_product_not_found():
    assert parse_product({"code": "1", "status": 0, "status_verbose": "product not found"}) is None


# ---------- router AI ----------


class Out(BaseModel):
    ok: bool = True


class FakeProvider:
    def __init__(self, name, tiers, limited=False):
        self.name, self.tiers, self.limited, self.calls = name, tiers, limited, 0

    def supports(self, tier):
        return tier in self.tiers

    def generate(self, tier, prompt, schema, images=None):
        self.calls += 1
        if self.limited:
            raise RateLimited
        return AiResult(data=schema(), provider=self.name, model=f"{self.name}-{tier}")


ALL = {Tier.CHEAP, Tier.MID, Tier.STRONG}


def test_router_uses_primary_provider():
    gemini, claude = FakeProvider("gemini", ALL), FakeProvider("claude", ALL)
    router = AiRouter({"gemini": gemini, "claude": claude})
    assert router.run(Task.MEAL_PHOTO, "p", Out).provider == "gemini"
    assert router.run(Task.WEEK_REVIEW, "p", Out).model == "claude-strong"


def test_router_falls_back_on_rate_limit():
    gemini, claude = FakeProvider("gemini", ALL, limited=True), FakeProvider("claude", ALL)
    result = AiRouter({"gemini": gemini, "claude": claude}).run(Task.MEAL_PHOTO, "p", Out)
    # Najpierw oba modele Gemini (każdy ma osobny limit), potem Claude.
    assert (result.provider, gemini.calls, claude.calls) == ("claude", 2, 1)


def test_router_falls_back_to_the_other_gemini_model():
    class FirstModelBusy(FakeProvider):
        def generate(self, tier, prompt, schema, images=None):
            self.calls += 1
            if tier == Tier.CHEAP:
                raise RateLimited
            return AiResult(data=schema(), provider=self.name, model=f"{self.name}-{tier}")

    gemini = FirstModelBusy("gemini", ALL)
    result = AiRouter({"gemini": gemini}).run(Task.TEXT_TO_ITEMS, "p", Out)
    assert (result.model, gemini.calls) == ("gemini-mid", 2)


def test_router_with_gemini_only_handles_every_task():
    """Stan na start: jest tylko darmowy klucz Gemini (bez poziomu `strong`)."""
    router = AiRouter({"gemini": FakeProvider("gemini", {Tier.CHEAP, Tier.MID})})
    for task in Task:
        assert router.run(task, "p", Out).provider == "gemini"


def test_router_reports_when_everything_fails():
    router = AiRouter({"gemini": FakeProvider("gemini", ALL, limited=True)})
    with pytest.raises(AllProvidersFailed, match="gemini: limit; claude: niedostępny"):
        router.run(Task.MEAL_PHOTO, "p", Out)


def test_meal_contract_has_no_database_ids():
    assert "generic_food_id" not in str(MealEstimate.model_json_schema())
    sample = {
        "items": [
            {
                "name_pl": "ryż biały gotowany",
                "name_en": "white rice, cooked",
                "category": "grains",
                "grams": 200,
                "grams_low": 150,
                "grams_high": 260,
                "per_100g_estimate": {
                    "kcal": 130,
                    "protein_g": 2.7,
                    "fat_g": 0.3,
                    "sat_fat_g": 0.1,
                    "carbs_g": 28,
                    "sugars_g": 0.1,
                    "fiber_g": 0.4,
                    "salt_g": 0.0,
                },
                "confidence": "medium",
            }
        ],
        "notes": None,
    }
    assert MealEstimate.model_validate(sample).items[0].category == "grains"


def test_off_micro_mapping_matches_seed_dictionary():
    import json
    from pathlib import Path

    from app.off.client import MICRO_FIELDS

    seed = Path(__file__).resolve().parents[2] / "seed" / "nutrients.json"
    ids = {row["id"] for row in json.loads(seed.read_text(encoding="utf-8"))["nutrients"]}
    assert set(MICRO_FIELDS) == ids
