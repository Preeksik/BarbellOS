"""Baza zbudowana migracjami (nie przez create_all) musi przyjmować zapisy.

Pozostałe testy tworzą tabele wprost z modeli, więc nie widzą różnic między modelami
a migracjami. Ten test przechodzi tę samą drogę co prawdziwa instalacja na SQLite:
`alembic upgrade head`, a potem zapisy przez API.
"""

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.models import Base, Food
from app.db.session import get_db
from app.main import create_app
from tests.conftest import INGEST_TOKEN, PASSWORD

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def migrated(tmp_path, settings):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logging"] = False
    command.upgrade(config, "head")

    engine = create_engine(url, connect_args={"check_same_thread": False})
    factory = sessionmaker(engine, expire_on_commit=False)

    def override_db():
        with factory() as db:
            yield db

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, base_url="https://testserver") as client:
        assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
        yield client, factory, engine
    engine.dispose()


def test_migrations_create_every_table_and_column_from_models(migrated):
    _, _, engine = migrated
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        in_database = {column["name"] for column in inspector.get_columns(table.name)}
        assert in_database == {column.name for column in table.columns}, table.name


def test_writes_work_on_a_migrated_sqlite_database(migrated):
    client, factory, _ = migrated

    probe = client.put(
        f"/api/probe/{uuid.uuid4()}", json={"client_created_at": "2026-11-16T10:00:00+01:00"}
    )
    assert probe.status_code == 200
    assert probe.json()["received_at"] is not None

    ingest = client.post(
        "/api/health/ingest",
        headers={"Authorization": f"Bearer {INGEST_TOKEN}"},
        json={"type": "weight", "starts": ["2026-11-16T07:00:00+01:00"], "values": [75.2]},
    )
    assert ingest.status_code == 200
    assert ingest.json()["inserted"] == 1

    with factory() as db:
        food = Food(
            kind="packaged", name="Napój", origin="user", macro_source="user", unit="ml", kcal=21
        )
        db.add(food)
        db.commit()
        food_id = food.id
    entry = client.put(
        f"/api/diary/entries/{uuid.uuid4()}",
        json={"date": "2026-11-16", "meal_slot": "snack", "food_id": food_id, "amount": 330},
    )
    assert entry.status_code == 200
    assert entry.json()["unit"] == "ml"
    assert entry.json()["created_at"] is not None
    assert client.get("/api/diary/2026-11-16").json()["totals"]["kcal"] == pytest.approx(69.3)


def test_old_activity_is_converted_to_lifestyle_and_training(tmp_path):
    """Migracja 0006: profil zapisany ze starym polem `activity` dostaje nowe pola."""
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'old_profile.db'}"
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logging"] = False
    command.upgrade(config, "0005")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO user_profile (id, sex, birth_date, height_cm, weight_kg, activity, "
                "goal, pace_kg_week, updated_at) VALUES (1, 'male', '1998-05-10', 180, 80, "
                "'very_active', 'lose', 0.5, '2026-11-17 10:00:00')"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT lifestyle, steps_per_day, strength_sessions_week, strength_minutes, "
                "cardio_minutes_week FROM user_profile"
            )
        ).one()
    engine.dispose()
    assert tuple(row) == ("physical", 5000, 6, 60, 0)


def check_old_ai_entries_become_products(url: str, prepare=None) -> None:
    """Migracja 0011: dawne wpisy z AI bez produktu dostają produkt (22.11.2026).

    Wspólne dla SQLite (tutaj) i Postgresa (`test_postgres.py`, w CI). `prepare` czyści bazę.
    """
    import datetime as dt

    import sqlalchemy as sa

    engine = create_engine(url)
    if prepare:
        prepare(engine)
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logging"] = False
    command.upgrade(config, "0010")

    entry = sa.table(
        "meal_entry",
        *(sa.column(c, t) for c, t in (
            ("id", sa.Uuid), ("date", sa.Date), ("meal_slot", sa.String), ("food_name", sa.String),
            ("amount", sa.Float), ("unit", sa.String), ("micros", sa.JSON),
            ("macro_source", sa.String), ("source", sa.String),
            ("created_at", sa.DateTime(timezone=True)), ("kcal", sa.Float),
            ("protein_g", sa.Float), ("carbs_g", sa.Float),
        )),
    )  # fmt: skip
    nutrient = sa.table(
        "nutrient", *(sa.column(c, sa.String) for c in ("id", "name_pl", "unit", "grp"))
    )
    micros = {"vit_c": {"amount": 6.0, "source": "estimated"}}
    rows = [
        ("Pączek z polewą", 80, 300, 4, 40, dt.datetime(2026, 11, 20, 8, tzinfo=dt.UTC)),
        # Ten sam produkt później: produkt bierze wartości z najnowszego wpisu.
        ("pączek  Z POLEWĄ", 100, 400, 5, 50, dt.datetime(2026, 11, 21, 8, tzinfo=dt.UTC)),
        ("Spaghetti z leczo", 400, 600, 24, 80, dt.datetime(2026, 11, 21, 13, tzinfo=dt.UTC)),
    ]
    with engine.begin() as conn:
        conn.execute(nutrient.insert().values(id="vit_c", name_pl="C", unit="mg", grp="vitamin"))
        conn.execute(
            entry.insert(),
            [
                {"id": uuid.uuid4(), "date": dt.date(2026, 11, 20), "meal_slot": "lunch",
                 "food_name": name, "amount": amount, "unit": "g", "micros": micros,
                 "macro_source": "estimated", "source": "photo", "created_at": at,
                 "kcal": kcal, "protein_g": protein, "carbs_g": carbs}
                for name, amount, kcal, protein, carbs, at in rows
            ],
        )  # fmt: skip

    command.upgrade(config, "head")

    with engine.connect() as conn:
        orphans = conn.execute(text("SELECT count(*) FROM meal_entry WHERE food_id IS NULL"))
        assert orphans.scalar() == 0
        foods = conn.execute(
            text("SELECT id, name, kcal, protein_g, fat_g, carbs_g, origin, macro_source"
                 " FROM food ORDER BY id")
        ).all()  # fmt: skip
        assert [(f.name, f.kcal, f.protein_g, f.fat_g, f.carbs_g) for f in foods] == [
            ("pączek  Z POLEWĄ", 400, 5, None, 50),  # 100 g = wartości na 100 g; brak = NULL
            ("Spaghetti z leczo", 150, 6, None, 20),  # 600 kcal w 400 g
        ]
        assert {(f.origin, f.macro_source) for f in foods} == {("ai", "estimated")}
        linked = conn.execute(
            text("SELECT food_id, count(*) FROM meal_entry GROUP BY food_id ORDER BY food_id")
        ).all()
        assert [n for _, n in linked] == [2, 1]  # oba pączki wskazują jeden produkt
        vit_c = conn.execute(
            text("SELECT amount_per_100g, source FROM food_nutrient WHERE food_id = :id"),
            {"id": foods[1].id},
        ).one()
        assert vit_c.amount_per_100g == pytest.approx(1.5) and vit_c.source == "estimated"
    engine.dispose()


def test_old_ai_entries_become_products(tmp_path):
    check_old_ai_entries_become_products(f"sqlite:///{tmp_path / 'old.db'}")
