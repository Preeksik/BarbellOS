"""Migracje i zapisy na prawdziwym Postgresie (jak na serwerze w Neon).

Pozostałe testy działają na SQLite. Ten plik uruchamia się tylko, gdy zmienna
POSTGRES_TEST_URL wskazuje pustą bazę testową, czyli w GitHub Actions (kontener postgres:17).
Render wdraża nową wersję dopiero, gdy te testy przejdą (`autoDeployTrigger: checksPass`).
Uwaga: test czyści schemat bazy, nigdy nie podawaj tu adresu bazy z danymi.
"""

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.models import Base
from app.db.session import get_db, get_session_factory
from app.main import create_app
from app.tools.copy_db import _url, copy

from .conftest import PASSWORD
from .test_copy_db import source as source  # noqa: F401 - fixture z danymi w SQLite
from .test_migrations import BACKEND

URL = os.environ.get("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(not URL, reason="brak POSTGRES_TEST_URL (test tylko w CI)")


def _alembic(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logging"] = False
    return config


@pytest.fixture
def pg():
    url = _url(URL)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade; create schema public"))
    command.upgrade(_alembic(url), "head")
    yield engine
    engine.dispose()


def test_migrations_match_models_on_postgres(pg):
    inspector = inspect(pg)
    for table in Base.metadata.sorted_tables:
        in_database = {column["name"] for column in inspector.get_columns(table.name)}
        assert in_database == {column.name for column in table.columns}, table.name


def test_downgrade_and_upgrade_again(pg):
    config = _alembic(_url(URL))
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_main_flows_write_on_postgres(pg, settings):
    factory = sessionmaker(pg, expire_on_commit=False)

    def override_db():
        with factory() as db:
            yield db

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_session_factory] = lambda: factory
    with TestClient(app, base_url="https://testserver") as client:
        assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
        food = client.put(
            f"/api/foods/custom/{uuid.uuid4()}",
            json={"name": "Owsianka", "unit": "g", "per_100": {"kcal": 372, "protein_g": 13}},
        ).json()
        entry = client.put(
            f"/api/diary/entries/{uuid.uuid4()}",
            json={"date": "2026-11-18", "meal_slot": "breakfast", "food_id": food["id"],
                  "amount": 60},
        )  # fmt: skip
        assert entry.status_code == 200
        estimate = {"name": "kawa", "per_100": {"kcal": 39}, "micros_per_100": {"calcium": 50}}
        assert client.put(
            f"/api/diary/entries/{uuid.uuid4()}",
            json={"date": "2026-11-18", "meal_slot": "breakfast", "amount": 200,
                  "estimate": estimate, "source": "text"},
        ).status_code == 200  # fmt: skip
        goals = dict.fromkeys(["kcal", "protein_g", "fat_g", "sat_fat_g", "carbs_g", "sugars_g",
                               "fiber_g", "salt_g"]) | {"kcal": 2200}  # fmt: skip
        assert client.put("/api/targets/2026-11-18", json={"goals": goals}).status_code == 200
        profile = {"sex": "male", "birth_date": "1998-05-10", "height_cm": 180, "weight_kg": 80,
                   "lifestyle": "sitting", "steps_per_day": 5000, "strength_sessions_week": 4,
                   "strength_minutes": 75, "goal": "lose", "pace_kg_week": 0.5}  # fmt: skip
        assert client.put("/api/profile", json=profile).status_code == 200
        meal = {"name": "Śniadanie", "items": [{"food_id": food["id"], "amount": 60}]}
        assert client.put(f"/api/meals/{uuid.uuid4()}", json=meal).status_code == 204
        day = client.get("/api/diary/2026-11-18").json()
        assert day["totals"]["kcal"] == pytest.approx(372 * 0.6 + 78)
        week = client.get("/api/diary/week/2026-11-18").json()
        assert week["logged_days"] == 1
        assert client.get("/api/foods/search", params={"q": "owsian"}).json()["foods"]


def test_copy_local_sqlite_to_postgres(pg, source):  # noqa: F811
    copied = copy(source, pg)
    assert copied["meal_entry"] == 1
    with pg.begin() as connection:
        new_id = connection.execute(
            text(
                "insert into food (kind, name, origin, macro_source, unit) "
                "values ('packaged', 'Nowy', 'user', 'user', 'g') returning id"
            )
        ).scalar_one()
    assert new_id == 2  # licznik Postgresa ustawiony za skopiowanymi wierszami
