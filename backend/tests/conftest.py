"""Wspólne przygotowanie testów: aplikacja na bazie SQLite w pamięci, bez sieci."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_off_fetcher
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


@pytest.fixture
def client(settings, db_factory, off_calls):
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
    # Adres https, bo ciasteczko sesji w trybie prod ma flagę Secure.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@pytest.fixture
def logged_in(client):
    response = client.post("/api/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    return client
