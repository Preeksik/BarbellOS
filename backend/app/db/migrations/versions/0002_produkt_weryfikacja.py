"""Produkt: jednostka (g/ml), data danych w źródle, znacznik weryfikacji.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-15 16:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "food", sa.Column("unit", sa.String(length=2), server_default="g", nullable=False)
    )
    op.add_column("food", sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("food", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("food", "verified_at")
    op.drop_column("food", "source_updated_at")
    op.drop_column("food", "unit")
