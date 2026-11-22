"""Dawne wpisy z AI bez produktu dostają produkt (22.11.2026).

Do tej pory szacunek ze zdjęcia lub opisu był tylko wpisem (`food_id` NULL), więc nie dało
się go zapisać w posiłku ani dodać ponownie. Od teraz serwer zakłada produkt przy zapisie
(`repo.food_from_estimate`). Ta migracja robi to samo dla wpisów sprzed zmiany: produkt
z wartościami na 100 g odtworzonymi z najnowszego wpisu o tej nazwie (`origin = ai`,
`macro_source = estimated`). Zamrożone wartości samych wpisów się nie zmieniają.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-22 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.diary import per_100_of_entry
from app.core.search import words

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MACROS = ("kcal", "protein_g", "fat_g", "sat_fat_g", "carbs_g", "sugars_g", "fiber_g", "salt_g")

entry = sa.table(
    "meal_entry",
    sa.column("id", sa.Uuid),
    sa.column("food_id", sa.Integer),
    sa.column("food_name", sa.String),
    sa.column("amount", sa.Float),
    sa.column("micros", sa.JSON),
    sa.column("created_at", sa.DateTime(timezone=True)),
    *(sa.column(m, sa.Float) for m in MACROS),
)
food = sa.table(
    "food",
    sa.column("id", sa.Integer),
    sa.column("kind", sa.String),
    sa.column("name", sa.String),
    sa.column("unit", sa.String),
    sa.column("origin", sa.String),
    sa.column("macro_source", sa.String),
    *(sa.column(m, sa.Float) for m in MACROS),
)
food_nutrient = sa.table(
    "food_nutrient",
    sa.column("food_id", sa.Integer),
    sa.column("nutrient_id", sa.String),
    sa.column("amount_per_100g", sa.Float),
    sa.column("source", sa.String),
)
nutrient = sa.table("nutrient", sa.column("id", sa.String))


def _key(name: str) -> str:
    return " ".join(words(name))


def upgrade() -> None:
    conn = op.get_bind()
    orphans = (
        conn.execute(
            sa.select(entry)
            .where(entry.c.food_id.is_(None), entry.c.amount > 0)
            .order_by(entry.c.created_at)
        )
        .mappings()
        .all()
    )
    if not orphans:
        return
    known = set(conn.execute(sa.select(nutrient.c.id)).scalars())
    existing = {
        _key(row.name): row.id
        for row in conn.execute(sa.select(food.c.id, food.c.name).where(food.c.origin == "ai"))
    }
    groups: dict[str, list] = {}
    for row in orphans:
        groups.setdefault(_key(row["food_name"]), []).append(row)

    for key, rows in groups.items():
        food_id = existing.get(key)
        if food_id is None:
            newest = rows[-1]  # najnowszy szacunek o tej nazwie
            per_100, micros_100 = per_100_of_entry(
                {m: newest[m] for m in MACROS}, newest["micros"], newest["amount"]
            )
            food_id = conn.execute(
                food.insert()
                .values(
                    kind="generic",
                    name=newest["food_name"][:255],
                    unit="g",
                    origin="ai",
                    macro_source="estimated",
                    **per_100,
                )
                .returning(food.c.id)
            ).scalar_one()
            nutrients = [
                {"food_id": food_id, "nutrient_id": nid, "amount_per_100g": amount, "source": src}
                for nid, (amount, src) in micros_100.items()
                if nid in known
            ]
            if nutrients:
                conn.execute(food_nutrient.insert(), nutrients)
        conn.execute(
            entry.update()
            .where(entry.c.id.in_([row["id"] for row in rows]))
            .values(food_id=food_id)
        )


def downgrade() -> None:
    # Produkty z szacunków mogą już być w zapisanych posiłkach: nie ma czego bezpiecznie cofać.
    pass
