"""Wpis dziennika: źródło wartości odżywczych (`macro_source`).

Etap 2 dodaje wpisy ze zdjęcia i opisu posiłku. Składnik, którego nie ma w bazie, ma
wartości oszacowane przez model (`estimated`). Każda wartość odżywcza musi mieć źródło
(AGENTS.md, zasada 7), więc wpis je zapisuje. Istniejące wpisy dostają źródło produktu.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("meal_entry") as batch:
        batch.add_column(sa.Column("macro_source", sa.String(length=16), nullable=True))
    op.execute(
        "UPDATE meal_entry SET macro_source = "
        "(SELECT food.macro_source FROM food WHERE food.id = meal_entry.food_id) "
        "WHERE food_id IS NOT NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("meal_entry") as batch:
        batch.drop_column("macro_source")
