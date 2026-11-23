"""Składniki dawki suplementu: witaminy z suplementów w pokryciu norm tygodnia (24.11.2026).

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-24 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplement_nutrient",
        sa.Column("supplement_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_id", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["supplement_id"], ["supplement.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nutrient_id"], ["nutrient.id"]),
        sa.PrimaryKeyConstraint("supplement_id", "nutrient_id"),
    )


def downgrade() -> None:
    op.drop_table("supplement_nutrient")
