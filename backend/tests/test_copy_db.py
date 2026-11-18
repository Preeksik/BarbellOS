"""Przenoszenie danych z lokalnej bazy na serwer (`app.tools.copy_db`)."""

import uuid
from datetime import UTC, date, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import DailyTarget, Food, MealEntry, Nutrient
from app.tools.copy_db import _url, copy, plan_copy

from .test_migrations import BACKEND


def migrated_engine(path):
    url = f"sqlite:///{path}"
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logging"] = False
    command.upgrade(config, "head")
    return create_engine(url)


@pytest.fixture
def source(tmp_path):
    engine = migrated_engine(tmp_path / "zrodlo.db")
    with Session(engine) as db:
        db.add(Nutrient(id="calcium", name_pl="Wapń", unit="mg", grp="mineral", rda=800))
        food = Food(kind="packaged", name="Gouda", origin="off", macro_source="label", kcal=356)
        db.add(food)
        db.flush()
        db.add(
            MealEntry(
                id=uuid.uuid4(),
                date=date(2026, 11, 18),
                meal_slot="dinner",
                food_id=food.id,
                food_name="Gouda",
                amount=200,
                kcal=712,
                micros={"calcium": {"amount": 1400, "source": "estimated"}},
                source="scan",
                created_at=datetime(2026, 11, 18, 19, tzinfo=UTC),
            )
        )
        db.add(DailyTarget(date_from=date(2026, 11, 17), nutrient_id="kcal", min=2230, max=2230))
        db.commit()
    yield engine
    engine.dispose()


def test_copy_to_empty_server_database(source, tmp_path):
    target = migrated_engine(tmp_path / "serwer.db")
    plan = {name: decision for name, _, decision in plan_copy(source, target)}
    assert plan["food"] == "kopiuj" and plan["meal_entry"] == "kopiuj"

    copied = copy(source, target)
    assert copied["food"] == 1 and copied["meal_entry"] == 1 and copied["nutrient"] == 1
    with Session(target) as db:
        entry = db.scalars(select(MealEntry)).one()
        assert (entry.food_name, entry.kcal) == ("Gouda", 712)
        assert entry.micros["calcium"]["amount"] == 1400
        assert entry.created_at.tzinfo is not None  # daty zostają w UTC ze strefą
        food = Food(kind="packaged", name="Nowy", origin="user", macro_source="user")
        db.add(food)
        db.commit()
        assert food.id == 2  # licznik id kontynuuje po skopiowanych wierszach
    target.dispose()


def test_refuses_to_merge_two_histories(source, tmp_path):
    target = migrated_engine(tmp_path / "serwer.db")
    copy(source, target)
    with pytest.raises(SystemExit, match="ma już dane w tabeli"):
        copy(source, target)
    target.dispose()


def test_skips_tables_seeded_by_the_server(source, tmp_path):
    target = migrated_engine(tmp_path / "serwer.db")
    with Session(target) as db:
        db.add(Nutrient(id="calcium", name_pl="Wapń", unit="mg", grp="mineral", rda=800))
        db.commit()
    plan = {name: decision for name, _, decision in plan_copy(source, target)}
    assert plan["nutrient"].startswith("pominięta: serwer wgrywa ją sam")
    assert "nutrient" not in copy(source, target)
    target.dispose()


def test_refuses_different_migration_versions(source, tmp_path):
    empty = create_engine(f"sqlite:///{tmp_path / 'pusta.db'}")
    with pytest.raises(SystemExit, match="Różne wersje migracji"):
        plan_copy(source, empty)


def test_url_uses_psycopg3():
    assert _url("postgres://u:p@h/db").startswith("postgresql+psycopg://")
    assert _url("sqlite:///./barbellos.db") == "sqlite:///./barbellos.db"
