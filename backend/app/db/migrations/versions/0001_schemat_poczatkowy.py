"""Schemat początkowy (dokumentacja, rozdział 8).

Revision ID: 0001
Revises:
Create Date: 2026-11-14 22:21:26.309320
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Double(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "daily_target",
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("nutrient_id", sa.String(length=32), nullable=False),
        sa.Column("min", sa.Double(), nullable=True),
        sa.Column("max", sa.Double(), nullable=True),
        sa.PrimaryKeyConstraint("date_from", "nutrient_id"),
    )
    op.create_table(
        "food",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("barcode", sa.String(length=14), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("serving_g", sa.Double(), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("macro_source", sa.String(length=16), nullable=False),
        sa.Column("generic_parent_id", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "raw",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("kcal", sa.Double(), nullable=True),
        sa.Column("protein_g", sa.Double(), nullable=True),
        sa.Column("fat_g", sa.Double(), nullable=True),
        sa.Column("sat_fat_g", sa.Double(), nullable=True),
        sa.Column("carbs_g", sa.Double(), nullable=True),
        sa.Column("sugars_g", sa.Double(), nullable=True),
        sa.Column("fiber_g", sa.Double(), nullable=True),
        sa.Column("salt_g", sa.Double(), nullable=True),
        sa.ForeignKeyConstraint(
            ["generic_parent_id"],
            ["food.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )
    op.create_table(
        "health_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sleep_min", sa.Double(), nullable=True),
        sa.Column("sleep_deep_min", sa.Double(), nullable=True),
        sa.Column("sleep_rem_min", sa.Double(), nullable=True),
        sa.Column("hrv_ms", sa.Double(), nullable=True),
        sa.Column("resting_hr", sa.Double(), nullable=True),
        sa.Column("weight_kg", sa.Double(), nullable=True),
        sa.Column("steps", sa.Double(), nullable=True),
        sa.Column("active_kcal", sa.Double(), nullable=True),
        sa.Column("readiness", sa.String(length=16), nullable=True),
        sa.Column(
            "factors",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("date"),
    )
    op.create_table(
        "health_sample",
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("value", sa.Double(), nullable=True),
        sa.Column("label", sa.String(length=32), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("type", "starts_at", "source"),
    )
    op.create_table(
        "nutrient",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name_pl", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("grp", sa.String(length=16), nullable=False),
        sa.Column("rda", sa.Double(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "offline_probe",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=128), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "coach_note",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("scope", sa.String(length=8), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ai_run_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ai_run_id"],
            ["ai_run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coach_note_date"), "coach_note", ["date"], unique=False)
    op.create_table(
        "food_alias",
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["food.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("food_id", "alias"),
    )
    op.create_table(
        "food_nutrient",
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("nutrient_id", sa.String(length=32), nullable=False),
        sa.Column("amount_per_100g", sa.Double(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["food.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["nutrient_id"],
            ["nutrient.id"],
        ),
        sa.PrimaryKeyConstraint("food_id", "nutrient_id"),
    )
    op.create_table(
        "meal_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_slot", sa.String(length=16), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=True),
        sa.Column("food_name", sa.String(length=255), nullable=False),
        sa.Column("grams", sa.Double(), nullable=False),
        sa.Column(
            "micros",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("ai_run_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("kcal", sa.Double(), nullable=True),
        sa.Column("protein_g", sa.Double(), nullable=True),
        sa.Column("fat_g", sa.Double(), nullable=True),
        sa.Column("sat_fat_g", sa.Double(), nullable=True),
        sa.Column("carbs_g", sa.Double(), nullable=True),
        sa.Column("sugars_g", sa.Double(), nullable=True),
        sa.Column("fiber_g", sa.Double(), nullable=True),
        sa.Column("salt_g", sa.Double(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ai_run_id"],
            ["ai_run.id"],
        ),
        sa.ForeignKeyConstraint(
            ["food_id"],
            ["food.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_entry_date"), "meal_entry", ["date"], unique=False)
    op.create_table(
        "plan_settings",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column(
            "tm",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("meet_date", sa.Date(), nullable=True),
        sa.Column(
            "adj",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("collars", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id"),
    )
    op.create_table(
        "session_log",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("session_key", sa.String(length=16), nullable=False),
        sa.Column("gym", sa.String(length=64), nullable=True),
        sa.Column("bodyweight", sa.Double(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", "session_key"),
    )
    op.create_table(
        "set_log",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("session_key", sa.String(length=16), nullable=False),
        sa.Column("ex_index", sa.Integer(), nullable=False),
        sa.Column("kg", sa.Double(), nullable=True),
        sa.Column("reps", sa.Double(), nullable=True),
        sa.Column("rpe", sa.Double(), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("ok", sa.String(length=1), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", "session_key", "ex_index"),
    )

    # Wyszukiwanie przybliżone po nazwie (dopasowanie składników z AI). Tylko Postgres.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        op.execute("CREATE INDEX ix_food_name_trgm ON food USING gin (name gin_trgm_ops)")
        op.execute("CREATE INDEX ix_food_name_en_trgm ON food USING gin (name_en gin_trgm_ops)")
        op.execute("CREATE INDEX ix_food_alias_trgm ON food_alias USING gin (alias gin_trgm_ops)")


def downgrade() -> None:
    op.drop_table("set_log")
    op.drop_table("session_log")
    op.drop_table("plan_settings")
    op.drop_index(op.f("ix_meal_entry_date"), table_name="meal_entry")
    op.drop_table("meal_entry")
    op.drop_table("food_nutrient")
    op.drop_table("food_alias")
    op.drop_index(op.f("ix_coach_note_date"), table_name="coach_note")
    op.drop_table("coach_note")
    op.drop_table("plan")
    op.drop_table("offline_probe")
    op.drop_table("nutrient")
    op.drop_table("health_sample")
    op.drop_table("health_daily")
    op.drop_table("food")
    op.drop_table("daily_target")
    op.drop_table("ai_run")
