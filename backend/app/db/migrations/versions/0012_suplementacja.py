"""Suplementacja: lista suplementów i odhaczanie, co wzięte danego dnia (23.11.2026).

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-23 23:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("dose", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "supplement_intake",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("supplement_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplement_id"], ["supplement.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("date", "supplement_id"),
    )


def downgrade() -> None:
    op.drop_table("supplement_intake")
    op.drop_table("supplement")
