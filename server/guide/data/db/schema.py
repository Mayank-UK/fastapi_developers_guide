"""The guide's schema as SQLAlchemy Core tables — the autogenerate source.

The initial Alembic migration (``alembic/versions/``) was generated from
these tables and committed; together they are the schema's single source
of truth, and ``alembic check`` (run in the test suite) refuses to let
the two drift. Topic 18's ORM classes will map onto these same ``Table``
objects rather than redeclaring columns.

The design is deliberately a TEACHING surface for topic 16: every
constraint kind worth knowing appears once, with a name — NOT NULL,
CHECK domains, UNIQUE, FK ON DELETE behaviors, server defaults, one
b-tree index per foreign key, and a partial index that only covers
published posts. The "bigserial" primary keys are spelled the way
PostgreSQL actually implements them — a ``bigint`` whose default pulls
from an explicit SEQUENCE — because the sequence IS the teaching point
(the explorer shows ``nextval('posts_id_seq')`` in the column default).
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CheckConstraint, MetaData, Sequence, Table

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
"""Deterministic constraint names: violations arrive in error messages as
NAMES, so unnamed constraints (``posts_pkey``, ``posts_status_check`` in
PostgreSQL's own spelling) are a debugging tax this convention removes."""

metadata = MetaData(naming_convention=NAMING_CONVENTION)

posts_id_seq = Sequence("posts_id_seq", metadata=metadata)
comments_id_seq = Sequence("comments_id_seq", metadata=metadata)
audit_log_id_seq = Sequence("audit_log_id_seq", metadata=metadata)
outbox_id_seq = Sequence("outbox_id_seq", metadata=metadata)
"""Explicit sequences = "bigserial" with the machinery visible: bigint
columns whose DEFAULT is nextval(seq) — see the tables below."""

authors = Table(
    "authors",
    metadata,
    sa.Column(
        "id",
        postgresql.UUID(),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    ),
    sa.Column("name", sa.Text(), nullable=False),
    sa.Column("email", sa.Text(), nullable=False, unique=True),
    sa.Column("bio", sa.Text(), nullable=False, server_default=""),
    sa.Column(
        "created_at",
        postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
)

posts = Table(
    "posts",
    metadata,
    sa.Column("id", sa.BigInteger(), server_default=posts_id_seq.next_value(), primary_key=True),
    sa.Column(
        "search_vector",
        postgresql.TSVECTOR(),
        sa.Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))",
            persisted=True,
        ),
    ),
    sa.Column(
        "author_id",
        postgresql.UUID(),
        sa.ForeignKey(authors.c.id, ondelete="RESTRICT"),
        nullable=False,
    ),
    sa.Column("slug", sa.Text(), nullable=False, unique=True),
    sa.Column("title", sa.Text(), nullable=False),
    sa.Column("body", sa.Text(), nullable=False, server_default=""),
    sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
    sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
    sa.Column(
        "created_at",
        postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
    sa.Column(
        "updated_at",
        postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
    sa.Column(
        "version",
        sa.Integer(),
        nullable=False,
        server_default=sa.text("1"),
    ),
    CheckConstraint("status IN ('draft', 'published')", name="status_domain"),
    CheckConstraint("char_length(title) BETWEEN 1 AND 120", name="title_length"),
)

comments = Table(
    "comments",
    metadata,
    sa.Column("id", sa.BigInteger(), server_default=comments_id_seq.next_value(), primary_key=True),
    sa.Column(
        "post_id",
        sa.BigInteger(),
        sa.ForeignKey(posts.c.id, ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("author", sa.Text(), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column(
        "created_at",
        postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
    CheckConstraint("char_length(body) <= 2000", name="body_length"),
)

audit_log = Table(
    "audit_log",
    metadata,
    sa.Column(
        "id", sa.BigInteger(), server_default=audit_log_id_seq.next_value(), primary_key=True
    ),
    sa.Column(
        "occurred_at",
        postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
    sa.Column("actor", sa.Text(), nullable=False),
    sa.Column("action", sa.Text(), nullable=False),
    sa.Column("table_name", sa.Text(), nullable=False),
    sa.Column("row_pk", sa.Text(), nullable=False),
    sa.Column(
        "changes",
        postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    ),
)

sa.Index("ix_posts_author_id", posts.c.author_id)
"""Plain b-tree on the FK: joins by author and the RESTRICT/DELETE checks
need it — PostgreSQL does NOT auto-index foreign keys."""

sa.Index("ix_comments_post_id", comments.c.post_id)
"""Same discipline one table down: every FK gets its index."""

sa.Index("ix_posts_search_vector", posts.c.search_vector, postgresql_using="gin")
"""A GIN index over the generated tsvector: full-text matches (``@@``) walk
the inverted index instead of recomputing the vector per row — the index
topic 17's search demo watches EXPLAIN actually use (migration 0002)."""

sa.Index(
    "ix_posts_published_created_at",
    posts.c.created_at,
    postgresql_where=sa.text("status = 'published'"),
)
"""A PARTIAL index: it only covers published posts, so drafts never bloat
it and the common query (published posts, newest first) reads a smaller
tree. WHERE appears in the explorer's introspection of the live schema."""

outbox = Table(
    "outbox",
    metadata,
    sa.Column(
        "id", sa.BigInteger(), server_default=outbox_id_seq.next_value(), primary_key=True
    ),
    sa.Column("event_id", postgresql.UUID(), nullable=False, unique=True),
    sa.Column("event_type", sa.Text(), nullable=False),
    sa.Column("aggregate", sa.Text(), nullable=False),
    sa.Column("payload", postgresql.JSONB(), nullable=False),
    sa.Column(
        "created_at",
        postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
    sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
)
"""Topic 22's transactional outbox: the events the business transaction
ALSO wrote, durable in the same PostgreSQL commit, waiting for the relay
to publish them and mark them gone. ``event_id`` is the app-minted UUIDv7
consumers dedupe on; ``published_at`` NULL is the relay's entire work
queue — which is exactly what the partial index below covers."""

sa.Index(
    "ix_outbox_unpublished",
    outbox.c.id,
    postgresql_where=sa.text("published_at IS NULL"),
)
"""A PARTIAL index over the relay's work queue: only unpublished rows,
in insertion order — the poll walks this small tree, never the whole
table, and rows leave the index the moment they are marked published."""
