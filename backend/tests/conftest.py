"""Wspólne przygotowanie testów: aplikacja na bazie SQLite w pamięci, bez sieci."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.provider import AiResult
from app.ai.router import AiRouter
from app.api.deps import get_ai_router, get_off_fetcher, get_off_searcher
from app.config import Settings, get_settings
from app.db.models import Base, Nutrient
from app.db.session import get_db
from app.main import create_app
from app.security import hash_password

PASSWORD = "bardzo-tajne-haslo"
INGEST_TOKEN = "token-testowy"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="prod",
        secret_key="test-secret-key",
        app_password_hash=hash_password(PASSWORD),
        ingest_token=INGEST_TOKEN,
        # Jawnie puste: klucz ze środowiska programisty nie może wysłać testów do sieci.
        gemini_api_key="",
        anthropic_api_key="",
    )


@pytest.fixture
def db_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        db.add_all(
            [
                Nutrient(id="calcium", name_pl="Wapń", unit="mg", grp="mineral", rda=800),
                Nutrient(id="vit_c", name_pl="Witamina C", unit="mg", grp="vitamin", rda=80),
            ]
        )
        db.commit()
    return factory


@pytest.fixture
def off_calls() -> list[str]:
    return []


# Odczyt z etykiety serka z `fake_fetch`, w kształcie `LabelExtract`.
LABEL_EXTRACT = {
    "name": "Serek wiejski",
    "brand": "Testowa",
    "basis": "100g",
    "serving_g": 200,
    "kcal": 97,
    "fat_g": 5,
    "sat_fat_g": 3.5,
    "carbs_g": 2,
    "sugars_g": 2,
    "fiber_g": None,
    "protein_g": 11,
    "salt_g": 0.7,
}


class FakeLabelAi:
    """Udaje dostawcę modeli: oddaje przygotowane odczyty albo rzuca przygotowane wyjątki."""

    name = "gemini"

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.outcomes: list[dict | Exception] = []  # kolejka; pusta = odczyt domyślny

    def supports(self, tier) -> bool:
        return True

    def generate(self, tier, prompt, schema, images=None) -> AiResult:
        self.calls.append({"tier": tier, "prompt": prompt, "images": images})
        outcome = self.outcomes.pop(0) if self.outcomes else LABEL_EXTRACT
        if isinstance(outcome, Exception):
            raise outcome
        return AiResult(
            data=schema.model_validate(outcome),
            provider=self.name,
            model="gemini-test",
            input_tokens=1500,
            output_tokens=120,
        )


@pytest.fixture
def label_ai() -> FakeLabelAi:
    return FakeLabelAi()


class FakeOffSearch:
    """Udaje search-a-licious: zapisuje zapytania i oddaje przygotowaną odpowiedź."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.payload: dict = {"hits": []}
        self.error: Exception | None = None

    def search(self, query: str) -> dict:
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def off_search() -> FakeOffSearch:
    return FakeOffSearch()


@pytest.fixture(autouse=True)
def fresh_search_limiter(monkeypatch):
    """Każdy test zaczyna z pustym limitem wyszukiwań w OFF."""
    from app.off.client import RateLimiter

    monkeypatch.setattr("app.api.diet.search_limiter", RateLimiter(limit=8, window_s=60.0))


@pytest.fixture
def client(settings, db_factory, off_calls, label_ai, off_search):
    from app.off.client import FoodDraft

    def fake_fetch(barcode: str):
        off_calls.append(barcode)
        if barcode != "5900000000015":
            return None
        return FoodDraft(
            barcode=barcode,
            name="Serek wiejski",
            brand="Testowa",
            category="en:cottage-cheeses",
            serving_g=200,
            macros={
                "kcal": 97,
                "protein_g": 11,
                "fat_g": 5,
                "sat_fat_g": 3.5,
                "carbs_g": 2,
                "sugars_g": 2,
                "fiber_g": None,
                "salt_g": 0.7,
            },  # fmt: skip
            micros={"calcium": 80.0, "nieznany": 1.0},
            raw={"code": barcode},
        )

    def override_db():
        with db_factory() as db:
            yield db

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_off_fetcher] = lambda: fake_fetch
    app.dependency_overrides[get_ai_router] = lambda: AiRouter(
        {"gemini": label_ai}, sleep=lambda _: None
    )
    app.dependency_overrides[get_off_searcher] = lambda: off_search.search
    # Adres https, bo ciasteczko sesji w trybie prod ma flagę Secure.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@pytest.fixture
def logged_in(client):
    response = client.post("/api/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    return client
