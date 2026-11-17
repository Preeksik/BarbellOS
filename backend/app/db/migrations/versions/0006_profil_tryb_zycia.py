"""Profil: tryb życia, kroki i treningi zamiast jednego współczynnika aktywności.

Dotychczasowe `activity` mieszało pracę, chodzenie i treningi. Teraz każdy składnik
zapotrzebowania ma osobne pole (dokumentacja 4.10). Istniejący profil dostaje wartości
odpowiadające staremu wyborowi.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-17 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# stara aktywność -> (tryb życia, treningi siłowe w tygodniu)
MAPPING = {
    "sedentary": ("sitting", 0),
    "light": ("sitting", 2),
    "moderate": ("sitting", 4),
    "active": ("mixed", 6),
    "very_active": ("physical", 6),
}


def upgrade() -> None:
    with op.batch_alter_table("user_profile") as batch:
        batch.add_column(
            sa.Column("lifestyle", sa.String(length=16), server_default="sitting", nullable=False)
        )
        batch.add_column(
            sa.Column("steps_per_day", sa.Integer(), server_default="5000", nullable=False)
        )
        batch.add_column(
            sa.Column("strength_sessions_week", sa.Integer(), server_default="0", nullable=False)
        )
        batch.add_column(
            sa.Column("strength_minutes", sa.Integer(), server_default="60", nullable=False)
        )
        batch.add_column(
            sa.Column("cardio_minutes_week", sa.Integer(), server_default="0", nullable=False)
        )
    for activity, (lifestyle, sessions) in MAPPING.items():
        op.execute(
            sa.text(
                "UPDATE user_profile SET lifestyle = :lifestyle, "
                "strength_sessions_week = :sessions WHERE activity = :activity"
            ).bindparams(lifestyle=lifestyle, sessions=sessions, activity=activity)
        )
    with op.batch_alter_table("user_profile") as batch:
        batch.drop_column("activity")


def downgrade() -> None:
    with op.batch_alter_table("user_profile") as batch:
        batch.add_column(
            sa.Column("activity", sa.String(length=16), server_default="moderate", nullable=False)
        )
        batch.drop_column("cardio_minutes_week")
        batch.drop_column("strength_minutes")
        batch.drop_column("strength_sessions_week")
        batch.drop_column("steps_per_day")
        batch.drop_column("lifestyle")
