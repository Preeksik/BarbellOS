"""Ustawienie talerzy: czy na siłowni są talerze 25 kg (25.11.2026).

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-25 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plan_settings",
        sa.Column("plates_25", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("plan_settings", "plates_25")
