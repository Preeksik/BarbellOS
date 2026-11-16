"""Etap 1, krok 3: zdjęcie etykiety i własny produkt dla kodu spoza Open Food Facts."""

import base64
import json

import httpx
import pytest
from sqlalchemy import select

from app.ai.gemini import API_REVISION, GeminiProvider
from app.ai.json_schema import provider_schema
from app.ai.prompts import LABEL_PROMPT
from app.ai.provider import InvalidResponse, ProviderUnavailable, RateLimited, Tier
from app.ai.router import AiRouter, AllProvidersFailed, FailureKind, Task
from app.ai.schemas import LabelExtract, MealEstimate
from app.config import Settings
from app.core.label import image_mime, label_draft
from app.db.models import AiRun
from tests.conftest import LABEL_EXTRACT

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
NEW_EAN = "4006381333931"  # poprawny kod, którego nie zna ani baza, ani OFF z conftest

# ---------- rozpoznanie formatu obrazu ----------


@pytest.mark.parametrize(
    ("data", "mime"),
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (b"RIFF\x10\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00", "image/heic"),
        (b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00", "image/heif"),
        (b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00", None),  # film, nie zdjęcie
        (b"%PDF-1.7", None),
        (b"GIF89a", None),
        (b"", None),
    ],
)
def test_image_type_is_recognised_by_content(data, mime):
    assert image_mime(data) == mime


# ---------- szkic z odczytu modelu ----------


def test_draft_keeps_values_and_leaves_missing_ones_empty():
    draft = label_draft(LABEL_EXTRACT)
    assert draft.unit == "g"
    assert draft.macros["kcal"] == 97
    assert draft.macros["sat_fat_g"] == 3.5
    assert draft.macros["fiber_g"] is None  # brak na etykiecie to brak, nie zero
    assert (draft.name, draft.brand, draft.serving_g) == ("Serek wiejski", "Testowa", 200)
    assert draft.found == 7
    assert draft.warnings == []


def test_draft_fills_only_zeros_that_follow_from_the_label():
    draft = label_draft({"basis": "100ml", "kcal": 0, "fat_g": 0, "carbs_g": 0, "protein_g": 0})
    assert draft.unit == "ml"
    assert draft.macros["sat_fat_g"] == 0  # tłuszcz 0 g, więc nasycone też
    assert draft.macros["sugars_g"] == 0
    assert draft.macros["fiber_g"] is None
    assert draft.macros["salt_g"] is None


def test_draft_drops_impossible_values_and_says_so():
    # 2029 to kJ przepisane w miejsce kcal; 140 g białka w 100 g nie istnieje.
    draft = label_draft({**LABEL_EXTRACT, "kcal": 2029, "protein_g": 140, "salt_g": -1})
    assert draft.macros["kcal"] is None
    assert draft.macros["protein_g"] is None
    assert draft.macros["salt_g"] is None
    assert draft.macros["fat_g"] == 5
    assert len(draft.warnings) == 3
    assert "Energia: odczytana wartość 2029 jest niemożliwa" in draft.warnings[0]


def test_draft_shows_contradictions_instead_of_guessing_which_number_is_wrong():
    draft = label_draft({**LABEL_EXTRACT, "sugars_g": 20})
    assert draft.macros["sugars_g"] == 20
    assert draft.macros["carbs_g"] == 2
    assert any("Cukry (20 g) nie mogą przekraczać" in w for w in draft.warnings)


def test_draft_warns_when_energy_does_not_match_macros():
    draft = label_draft({**LABEL_EXTRACT, "kcal": 790})
    assert draft.macros["kcal"] == 790
    assert any("nie pasuje do makroskładników" in w for w in draft.warnings)


def test_draft_without_per_100_column():
    empty = label_draft({"basis": "other", "name": "  Baton \n proteinowy "})
    assert empty.found == 0
    assert empty.unit is None
    assert empty.name == "Baton proteinowy"
    assert empty.warnings == []

    unsure = label_draft({"basis": "other", "kcal": 250})
    assert unsure.unit is None
    assert "na 100 g, czy na 100 ml" in unsure.warnings[0]


def test_draft_cleans_text_numbers_and_serving():
    draft = label_draft(
        {
            "basis": "100g",
            "name": "",
            "brand": "x" * 400,
            "serving_g": 0,
            "kcal": 97.123456,
            "fat_g": float("nan"),
            "carbs_g": "12",  # tekst zamiast liczby: nie zgadujemy
            "protein_g": True,
        }
    )
    assert draft.name is None
    assert len(draft.brand) == 255
    assert draft.serving_g is None
    assert draft.macros["kcal"] == 97.12
    assert draft.macros["fat_g"] is None
    assert draft.macros["carbs_g"] is None
    assert draft.macros["protein_g"] is None


# ---------- schemat dla dostawcy ----------


def _keys(node) -> set[str]:
    """Słowa kluczowe użyte w schemacie (bez nazw pól)."""
    if isinstance(node, list):
        return set().union(*map(_keys, node)) if node else set()
    if not isinstance(node, dict):
        return set()
    found = set(node)
    for key, value in node.items():
        found |= set().union(*map(_keys, value.values())) if key == "properties" else _keys(value)
    return found


def test_label_schema_uses_only_documented_keywords():
    schema = provider_schema(LabelExtract)
    assert _keys(schema) <= {"type", "properties", "required", "description", "enum"}
    props = schema["properties"]
    assert props["kcal"]["type"] == ["number", "null"]
    assert props["name"]["type"] == ["string", "null"]
    assert props["basis"] == {
        "type": "string",
        "enum": ["100g", "100ml", "other"],
        "description": props["basis"]["description"],
    }
    # Każde pole jest wymagane: model ma jawnie napisać null, a nie pominąć wartość.
    assert set(schema["required"]) == set(props) == set(LABEL_EXTRACT)


def test_nested_models_are_inlined():
    schema = provider_schema(MealEstimate)
    assert not _keys(schema) & {"$ref", "$defs", "title", "default"}
    item = schema["properties"]["items"]["items"]
    assert "grains" in item["properties"]["category"]["enum"]
    assert item["properties"]["per_100g_estimate"]["properties"]["kcal"]["type"] == "number"
    assert schema["properties"]["notes"]["type"] == ["string", "null"]


def test_label_contract_and_prompt_ask_for_no_arithmetic_and_no_database_ids():
    assert "food_id" not in str(provider_schema(LabelExtract))
    assert "Niczego nie przeliczaj" in LABEL_PROMPT
    assert "Nie zgaduj" in LABEL_PROMPT


# ---------- dostawca Gemini (bez sieci) ----------


def _interaction(text: str, status: str = "completed") -> dict:
    return {
        "id": "v1_test",
        "status": status,
        "steps": [
            {"type": "thought", "content": [{"type": "text", "text": "pomijany"}]},
            {"type": "model_output", "content": [{"type": "text", "text": text}]},
        ],
        "usage": {
            "total_input_tokens": 1810,
            "total_output_tokens": 90,
            "total_thought_tokens": 40,
        },
    }


def _gemini(handler) -> GeminiProvider:
    return GeminiProvider(
        "klucz-testowy",
        {Tier.CHEAP: "gemini-test-lite"},
        base_url="https://gemini.test/",
        transport=httpx.MockTransport(handler),
    )


def test_gemini_sends_image_and_schema_and_reads_the_answer():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_interaction(json.dumps(LABEL_EXTRACT)))

    result = _gemini(handler).generate(Tier.CHEAP, LABEL_PROMPT, LabelExtract, images=[JPEG])

    assert result.data.kcal == 97
    assert result.data.fiber_g is None
    assert (result.provider, result.model) == ("gemini", "gemini-test-lite")
    assert (result.input_tokens, result.output_tokens) == (1810, 130)  # wyjście + myślenie

    (request,) = seen
    assert str(request.url) == "https://gemini.test/v1beta/interactions"
    assert request.headers["x-goog-api-key"] == "klucz-testowy"
    assert request.headers["api-revision"] == API_REVISION
    body = json.loads(request.content)
    assert body["model"] == "gemini-test-lite"
    assert body["store"] is False
    assert body["input"][0] == {"type": "text", "text": LABEL_PROMPT}
    assert body["input"][1] == {
        "type": "image",
        "data": base64.b64encode(JPEG).decode(),
        "mime_type": "image/jpeg",
    }
    assert body["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": provider_schema(LabelExtract),
    }


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(429, json={"error": {"message": "quota"}}), RateLimited),
        (httpx.Response(503, json={"error": {"message": "overloaded"}}), ProviderUnavailable),
        (httpx.Response(403, text="forbidden"), ProviderUnavailable),
        (httpx.Response(200, text="<html>"), ProviderUnavailable),
        (httpx.Response(200, json=_interaction("", status="failed")), ProviderUnavailable),
        (httpx.Response(200, json=_interaction("to nie jest JSON")), InvalidResponse),
        (httpx.Response(200, json=_interaction('{"kcal": 97}')), InvalidResponse),
        (httpx.Response(200, json=_interaction('{"kcal": 9', "incomplete")), InvalidResponse),
        (httpx.Response(200, json={"status": "completed"}), InvalidResponse),
    ],
)
def test_gemini_maps_failures(response, error):
    with pytest.raises(error):
        _gemini(lambda request: response).generate(Tier.CHEAP, "p", LabelExtract, images=[JPEG])


def test_gemini_network_error_and_missing_key():
    def no_network(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("brak sieci", request=request)

    with pytest.raises(ProviderUnavailable, match="ConnectTimeout"):
        _gemini(no_network).generate(Tier.CHEAP, "p", LabelExtract)

    without_key = GeminiProvider("", {Tier.CHEAP: "gemini-test-lite"})
    assert not without_key.supports(Tier.CHEAP)
    assert not _gemini(no_network).supports(Tier.STRONG)
    with pytest.raises(ProviderUnavailable):
        without_key.generate(Tier.CHEAP, "p", LabelExtract)


def test_gemini_error_never_contains_the_key():
    response = httpx.Response(400, json={"error": {"message": "API key not valid"}})
    with pytest.raises(ProviderUnavailable) as caught:
        _gemini(lambda request: response).generate(Tier.CHEAP, "p", LabelExtract)
    assert "klucz-testowy" not in str(caught.value)
    assert "HTTP 400" in str(caught.value)


# ---------- router: ponowienie przy złej odpowiedzi ----------


def test_router_retries_once_on_invalid_response(label_ai):
    label_ai.outcomes = [InvalidResponse("zły JSON")]
    result = AiRouter({"gemini": label_ai}).run(Task.LABEL_TO_FOOD, "p", LabelExtract)
    assert result.data.kcal == 97
    assert len(label_ai.calls) == 2


def test_router_gives_up_after_second_invalid_response(label_ai):
    label_ai.outcomes = [InvalidResponse("1"), InvalidResponse("2")]
    with pytest.raises(AllProvidersFailed) as caught:
        AiRouter({"gemini": label_ai}).run(Task.LABEL_TO_FOOD, "p", LabelExtract)
    assert len(label_ai.calls) == 2
    assert caught.value.kind == FailureKind.INVALID
    assert [f.provider for f in caught.value.called] == ["gemini"]


def test_router_without_any_key_reports_not_configured():
    with pytest.raises(AllProvidersFailed) as caught:
        AiRouter({}).run(Task.LABEL_TO_FOOD, "p", LabelExtract)
    assert caught.value.kind == FailureKind.NOT_CONFIGURED
    assert caught.value.called == []


def test_router_from_settings_uses_configured_models():
    from app.api.deps import get_ai_router

    settings = Settings(_env_file=None, gemini_api_key="k", gemini_model_cheap="model-tani")
    gemini = get_ai_router(settings).providers["gemini"]
    assert gemini.models[Tier.CHEAP] == "model-tani"
    assert gemini.supports(Tier.MID) and not gemini.supports(Tier.STRONG)
    # Klucz Claude dodany przed etapem 2 nie wywraca żądania: router idzie dalej.
    claude = get_ai_router(Settings(_env_file=None, anthropic_api_key="k")).providers["claude"]
    with pytest.raises(ProviderUnavailable):
        claude.generate(Tier.CHEAP, "p", LabelExtract)


# ---------- POST /api/foods/label ----------


def _scan(client, data: bytes = JPEG, content_type: str = "image/jpeg"):
    return client.post("/api/foods/label", content=data, headers={"Content-Type": content_type})


def _runs(db_factory) -> list[AiRun]:
    with db_factory() as db:
        return list(db.scalars(select(AiRun).order_by(AiRun.id)))


def test_label_requires_login(client, label_ai):
    assert _scan(client).status_code == 401
    assert label_ai.calls == []


def test_label_returns_draft_and_saves_nothing_but_the_ai_run(logged_in, label_ai, db_factory):
    response = _scan(logged_in)
    assert response.status_code == 200
    draft = response.json()
    assert draft["name"] == "Serek wiejski"
    assert draft["unit"] == "g"
    assert draft["serving_g"] == 200
    assert draft["per_100"]["kcal"] == 97
    assert draft["per_100"]["fiber_g"] is None
    assert draft["warnings"] == []

    (call,) = label_ai.calls
    assert call["tier"] == Tier.CHEAP
    assert call["images"] == [JPEG]
    assert call["prompt"] == LABEL_PROMPT

    (run,) = _runs(db_factory)
    assert (run.task, run.provider, run.model, run.status) == (
        "label_to_food",
        "gemini",
        "gemini-test",
        "ok",
    )
    assert (run.input_tokens, run.output_tokens, run.cost_usd) == (1500, 120, None)
    # Szkic to nie produkt: w bazie nic nie przybyło.
    assert logged_in.get(f"/api/foods/barcode/{NEW_EAN}").status_code == 404


def test_label_passes_code_warnings_to_the_form(logged_in, label_ai):
    label_ai.outcomes = [{**LABEL_EXTRACT, "kcal": 2029, "basis": "100ml"}]
    draft = _scan(logged_in, PNG, "image/png").json()
    assert draft["unit"] == "ml"
    assert draft["per_100"]["kcal"] is None
    assert "Energia: odczytana wartość 2029 jest niemożliwa" in draft["warnings"][0]


def test_label_rejects_files_that_are_not_photos(logged_in, label_ai):
    response = _scan(logged_in, b"%PDF-1.7 to nie jest zdjecie")
    assert response.status_code == 415
    assert _scan(logged_in, b"").status_code == 415
    assert label_ai.calls == []  # model nie jest wołany dla śmieci


def test_label_rejects_oversized_upload(logged_in, label_ai, monkeypatch):
    monkeypatch.setattr("app.api.diet.MAX_LABEL_IMAGE_BYTES", 32)
    response = _scan(logged_in)
    assert response.status_code == 413
    assert "za duże" in response.json()["detail"]
    assert label_ai.calls == []


def test_label_without_nutrition_table(logged_in, label_ai, db_factory):
    label_ai.outcomes = [dict.fromkeys(LABEL_EXTRACT) | {"basis": "other"}]
    response = _scan(logged_in)
    assert response.status_code == 422
    assert "Nie widzę na zdjęciu tabeli" in response.json()["detail"]
    assert [run.status for run in _runs(db_factory)] == ["ok"]  # wywołanie było i kosztuje


@pytest.mark.parametrize(
    ("outcomes", "status", "fragment", "logged"),
    [
        ([RateLimited()], 429, "limit modelu jest wyczerpany", ["rate_limited"]),
        ([InvalidResponse("a"), InvalidResponse("b")], 502, "nie odczytał etykiety", ["invalid"]),
        ([ProviderUnavailable("HTTP 503")], 502, "nie odpowiada", ["error"]),
    ],
)
def test_label_ai_failures_are_visible(
    logged_in, label_ai, db_factory, outcomes, status, fragment, logged
):
    label_ai.outcomes = outcomes
    response = _scan(logged_in)
    assert response.status_code == status
    assert fragment in response.json()["detail"]
    assert [run.status for run in _runs(db_factory)] == logged


def test_label_without_api_key_says_so(logged_in, db_factory):
    from app.api.deps import get_ai_router

    logged_in.app.dependency_overrides.pop(get_ai_router)  # prawdziwy router, puste klucze
    response = _scan(logged_in)
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]
    assert _runs(db_factory) == []  # żadnego wywołania nie było


# ---------- PUT /api/foods/barcode/{kod}: własny produkt ----------

OWN = {
    "name": "Baton proteinowy",
    "brand": "Lokalna",
    "serving_g": 60,
    "unit": "g",
    "origin": "ai_label",
    "per_100": {
        "kcal": 380, "protein_g": 30, "fat_g": 14, "sat_fat_g": 6,
        "carbs_g": 32, "sugars_g": 4, "fiber_g": None, "salt_g": 0.5,
    },
}  # fmt: skip


def test_create_requires_login(client):
    assert client.put(f"/api/foods/barcode/{NEW_EAN}", json=OWN).status_code == 401


def test_product_missing_from_off_can_be_created_from_label(logged_in, off_calls):
    assert logged_in.get(f"/api/foods/barcode/{NEW_EAN}").status_code == 404

    response = logged_in.put(f"/api/foods/barcode/{NEW_EAN}", json=OWN)
    assert response.status_code == 200
    food = response.json()
    assert food["barcode"] == NEW_EAN
    assert food["origin"] == "ai_label"
    assert food["macro_source"] == "user"  # wartości zatwierdził człowiek
    assert food["verified_at"] is not None
    assert food["serving_g"] == 60
    assert food["per_100"]["fiber_g"] is None
    assert food["per_100"]["protein_g"] == 30

    # Kolejny skan trafia we własną bazę, bez pytania Open Food Facts.
    again = logged_in.get(f"/api/foods/barcode/{NEW_EAN}").json()
    assert (again["id"], again["cached"]) == (food["id"], True)
    assert off_calls == [NEW_EAN]


def test_create_is_idempotent(logged_in):
    first = logged_in.put(f"/api/foods/barcode/{NEW_EAN}", json=OWN).json()
    second = logged_in.put(f"/api/foods/barcode/{NEW_EAN}", json=OWN).json()
    assert second["id"] == first["id"]
    assert second["per_100"] == first["per_100"]
    assert second["origin"] == "ai_label"


def test_put_by_barcode_on_known_product_corrects_it(logged_in):
    known = "5900000000015"
    original = logged_in.get(f"/api/foods/barcode/{known}").json()
    saved = logged_in.put(f"/api/foods/barcode/{known}", json=OWN).json()
    assert saved["id"] == original["id"]
    assert saved["origin"] == "off"  # pochodzenie rekordu się nie zmienia
    assert saved["macro_source"] == "user"
    assert saved["per_100"]["kcal"] == 380


def test_manual_product_defaults_to_user_origin(logged_in):
    body = {k: v for k, v in OWN.items() if k != "origin"}
    assert logged_in.put(f"/api/foods/barcode/{NEW_EAN}", json=body).json()["origin"] == "user"


@pytest.mark.parametrize(
    ("ean", "changes", "fragment"),
    [
        ("5900000000016", {}, "Nieprawidłowy kod kreskowy"),
        (NEW_EAN, {"name": "  "}, "Nazwa nie może być pusta"),
        (NEW_EAN, {"per_100": {**OWN["per_100"], "sugars_g": 50}}, "Cukry (50 g) nie mogą"),
        (NEW_EAN, {"origin": "off"}, None),
        (NEW_EAN, {"unit": "szt"}, None),
    ],
)
def test_create_rejects_impossible_products(logged_in, ean, changes, fragment):
    response = logged_in.put(f"/api/foods/barcode/{ean}", json={**OWN, **changes})
    assert response.status_code == 422
    if fragment:
        assert fragment in response.json()["detail"]
    assert logged_in.get(f"/api/foods/barcode/{NEW_EAN}").status_code == 404


def test_created_product_can_go_to_the_diary(logged_in):
    food = logged_in.put(f"/api/foods/barcode/{NEW_EAN}", json=OWN).json()
    entry = {"date": "2026-11-17", "meal_slot": "snack", "food_id": food["id"], "amount": 60}
    saved = logged_in.put("/api/diary/entries/0b0f3c1e-6f0a-4b7e-9d53-0c8a2f1d9e11", json=entry)
    assert saved.status_code == 200
    assert saved.json()["values"]["kcal"] == pytest.approx(228)
    assert saved.json()["values"]["fiber_g"] is None
