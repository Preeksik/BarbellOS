"""Produkt: kiedy automat sprawdzał go w tabeli USDA (`fdc_checked_at`).

Bez znacznika produkt bez pewnego dopasowania byłby wyszukiwany przy każdym otwarciu
tygodnia i każdym wpisie, co zużywa limit zapytań USDA i wywołania modelu.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-18 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("food") as batch:
        batch.add_column(sa.Column("fdc_checked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("food") as batch:
        batch.drop_column("fdc_checked_at")
