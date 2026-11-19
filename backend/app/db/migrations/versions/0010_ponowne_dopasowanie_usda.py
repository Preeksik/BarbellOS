"""Produkty bez dopasowania do USDA sprawdzane jeszcze raz (niższy próg, 19.11.2026).

Próg automatycznego dopasowania spadł z 0,5 do 0,35 (`core/micros.py`). Produkty, które
automat odrzucił przy starym progu, mają `fdc_checked_at` i nie byłyby sprawdzane
ponownie. Zdjęcie znacznika daje im drugą szansę przy następnym otwarciu tygodnia.
Same dane produktów (kalorie, makro, dopasowania już przyjęte) się nie zmieniają.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-19 02:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE food SET fdc_checked_at = NULL WHERE fdc_id IS NULL")


def downgrade() -> None:
    # Znacznik to tylko pamięć „już szukano"; nie ma czego przywracać.
    pass
