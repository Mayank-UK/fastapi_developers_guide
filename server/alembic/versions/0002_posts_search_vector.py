"""Full-text search arrives: a generated tsvector column + a GIN index.

Revision 0001 left posts searchable only by exact filters; this revision
adds the PostgreSQL-native search path topic 17 teaches. The column is
GENERATED ALWAYS ... STORED — PostgreSQL derives it from title and body
on every write, so it can never drift from the row it indexes — and the
expression lives in ONE place (here + the Core schema it was diffed
against). The GIN index over it is what turns ``search_vector @@ query``
from a per-row recomputation into an inverted-index lookup.

Additive only: no existing column changes, no table is dropped or
renamed — the honest shape of a migration applied to a running system.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_VECTOR_EXPRESSION: str = (
    "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))"
)
"""One spelling, shared with guide/data/db/schema.py's Computed column —
the migration and the Core metadata must agree or ``alembic check`` bites."""


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_EXPRESSION, persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_posts_search_vector",
        "posts",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_posts_search_vector", table_name="posts", postgresql_using="gin")
    op.drop_column("posts", "search_vector")
