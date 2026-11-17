"""Profil użytkownika: dane do szacowania zapotrzebowania i cel (redukcja, utrzymanie, masa).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-17 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(length=8), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("height_cm", sa.Double(), nullable=False),
        sa.Column("weight_kg", sa.Double(), nullable=False),
        sa.Column("activity", sa.String(length=16), nullable=False),
        sa.Column("goal", sa.String(length=8), nullable=False),
        sa.Column("pace_kg_week", sa.Double(), nullable=False),
        sa.Column("protein_g_per_kg", sa.Double(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("user_profile")
