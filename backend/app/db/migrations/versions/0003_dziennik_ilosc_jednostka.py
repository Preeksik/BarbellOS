"""Wpis dziennika: kolumna `grams` staje się `amount`, dochodzi jednostka (g/ml).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16 01:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table: na Postgresie zwykłe ALTER, na SQLite przepisanie tabeli.
    with op.batch_alter_table("meal_entry") as batch:
        batch.alter_column("grams", new_column_name="amount")
        batch.add_column(sa.Column("unit", sa.String(length=2), server_default="g", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("meal_entry") as batch:
        batch.drop_column("unit")
        batch.alter_column("amount", new_column_name="grams")
