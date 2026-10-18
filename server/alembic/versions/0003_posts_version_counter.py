"""Optimistic versioning arrives: a counter column on posts.

Topic 18's ORM maps ``version_id_col`` onto ``posts.version`` so every
UPDATE carries ``WHERE version = <the version you loaded>`` — two
sessions that loaded the same row cannot both commit; the loser's UPDATE
matches zero rows and SQLAlchemy raises ``StaleDataError`` instead of
silently overwriting (the lost update topic 17 needed SELECT … FOR
UPDATE to prevent, here refused by a plain column).

Additive and honest: existing rows backfill to version 1 through the
column's server default (PostgreSQL fills them at ADD COLUMN time — no
separate UPDATE pass), and the downgrade drops exactly what the upgrade
added. The Core schema in ``guide/data/db/schema.py`` grows the same
column, so ``alembic check`` keeps finding no drift.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("posts", "version")
