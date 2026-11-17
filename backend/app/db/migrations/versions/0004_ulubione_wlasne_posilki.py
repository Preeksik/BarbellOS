"""Etap 1, kroki 5 i 6: ulubione, produkt bez kodu, zapisane posiłki.

- `food.favorite_at`: kiedy produkt trafił do ulubionych (NULL = nie jest ulubiony),
- `food.client_id`: identyfikator nadany na telefonie produktowi bez kodu kreskowego,
  żeby powtórzona wysyłka z kolejki offline nie tworzyła duplikatu,
- `meal_template` i `meal_template_item`: zestawy produktów dodawane jednym stuknięciem.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("food") as batch:
        batch.add_column(sa.Column("favorite_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("client_id", sa.Uuid(), nullable=True))
        batch.create_unique_constraint("uq_food_client_id", ["client_id"])

    op.create_table(
        "meal_template",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "meal_template_item",
        sa.Column("meal_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Double(), nullable=False),
        sa.ForeignKeyConstraint(["meal_id"], ["meal_template.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["food.id"]),
        sa.PrimaryKeyConstraint("meal_id", "position"),
    )


def downgrade() -> None:
    op.drop_table("meal_template_item")
    op.drop_table("meal_template")
    with op.batch_alter_table("food") as batch:
        batch.drop_constraint("uq_food_client_id", type_="unique")
        batch.drop_column("client_id")
        batch.drop_column("favorite_at")
