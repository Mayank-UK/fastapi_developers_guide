"""The transactional outbox arrives: events as rows in PostgreSQL.

Topic 22's core table. The business transaction writes its post AND the
event that describes it in ONE commit — the outbox row IS the dual write
made atomic — and a relay later publishes unpublished rows to a Redis
Stream and stamps ``published_at``. ``event_id`` is the app-minted UUIDv7
(``guide.domain.db.ids``) consumers dedupe on: redelivery carries the
SAME id, so the exactly-once EFFECT is at-least-once delivery plus an
idempotent consumer, never a promise from the broker.

Shape notes: the bigint ``id`` keeps insertion order explicit (the relay
polls in id order — a stable cursor); ``published_at`` NULL is the entire
work queue, and the partial index covers exactly those rows, so the poll
walks a small tree that shrinks as the relay catches up. The downgrade
drops exactly what the upgrade added, index first.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The "bigserial" spelling this schema uses everywhere: an explicit
    # SEQUENCE plus a bigint whose DEFAULT pulls the next value.
    op.execute(sa.schema.CreateSequence(sa.Sequence("outbox_id_seq")))

    op.create_table(
        "outbox",
        sa.Column(
            "id",
            sa.BigInteger(),
            server_default=sa.text("nextval('outbox_id_seq'::regclass)"),
            nullable=False,
        ),
        sa.Column("event_id", postgresql.UUID(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("aggregate", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox")),
        sa.UniqueConstraint("event_id", name=op.f("uq_outbox_event_id")),
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_outbox_unpublished ON outbox (id) "
            "WHERE published_at IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_unpublished", table_name="outbox")
    op.drop_table("outbox")
    op.execute(sa.schema.DropSequence(sa.Sequence("outbox_id_seq")))
