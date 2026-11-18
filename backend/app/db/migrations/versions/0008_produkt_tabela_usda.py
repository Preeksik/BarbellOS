"""Produkt: dopasowanie do tabeli USDA FoodData Central (etap 6).

`fdc_id` i `fdc_description` mówią, z którego rekordu USDA pochodzą mikroskładniki
produktu (`food_nutrient` ze źródłem `reference` albo `estimated`).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("food") as batch:
        batch.add_column(sa.Column("fdc_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("fdc_description", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("food") as batch:
        batch.drop_column("fdc_description")
        batch.drop_column("fdc_id")
