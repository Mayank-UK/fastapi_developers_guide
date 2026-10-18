"""The guide's initial schema: authors, posts, comments, audit_log.

Generated from ``guide/data/db/schema.py`` via
``alembic revision --autogenerate`` and adjusted by hand (Alembic never
autogenerates SEQUENCEs — the three sequence creations and the
``nextval`` defaults were added where the source tables declare them).

Every constraint appears ONCE, with a NAME (the naming convention in the
source module): NOT NULL everywhere data is required; CHECK domains for
status/title/body; UNIQUE for slugs and emails; FKs with deliberate ON
DELETE behaviors (RESTRICT protects authors, CASCADE cleans comments);
server defaults for every column an INSERT may omit; one b-tree index
per foreign key; and one PARTIAL index covering only published posts.

Revision ID: 0001
Revises:
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # "Bigserial" primary keys, spelled the way PostgreSQL implements
    # them: an explicit SEQUENCE plus a bigint column whose DEFAULT
    # pulls the next value — the machinery topic 16's explorer shows.
    # (Alembic 1.20 dropped op.create_sequence; the DDL constructs run
    # through op.execute, dialect-rendered like every other statement.)
    op.execute(sa.schema.CreateSequence(sa.Sequence("posts_id_seq")))
    op.execute(sa.schema.CreateSequence(sa.Sequence("comments_id_seq")))
    op.execute(sa.schema.CreateSequence(sa.Sequence("audit_log_id_seq")))

    op.create_table(
        "authors",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("bio", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authors")),
        sa.UniqueConstraint("email", name=op.f("uq_authors_email")),
    )

    op.create_table(
        "posts",
        sa.Column(
            "id",
            sa.BigInteger(),
            server_default=sa.text("nextval('posts_id_seq'::regclass)"),
            nullable=False,
        ),
        sa.Column("author_id", postgresql.UUID(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published')", name=op.f("ck_posts_status_domain")
        ),
        sa.CheckConstraint(
            "char_length(title) BETWEEN 1 AND 120", name=op.f("ck_posts_title_length")
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["authors.id"],
            name=op.f("fk_posts_author_id_authors"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
        sa.UniqueConstraint("slug", name=op.f("uq_posts_slug")),
    )

    op.create_table(
        "comments",
        sa.Column(
            "id",
            sa.BigInteger(),
            server_default=sa.text("nextval('comments_id_seq'::regclass)"),
            nullable=False,
        ),
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(body) <= 2000", name=op.f("ck_comments_body_length")
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_comments_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            sa.BigInteger(),
            server_default=sa.text("nextval('audit_log_id_seq'::regclass)"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("row_pk", sa.Text(), nullable=False),
        sa.Column(
            "changes",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )

    # PostgreSQL does NOT auto-index foreign keys: every FK join and
    # every ON DELETE check would otherwise scan the table. One b-tree
    # per FK, by hand.
    op.create_index("ix_posts_author_id", "posts", ["author_id"], unique=False)
    op.create_index("ix_comments_post_id", "comments", ["post_id"], unique=False)
    # A PARTIAL index: only published posts are covered, so drafts never
    # bloat the tree the "newest published first" query reads.
    op.create_index(
        "ix_posts_published_created_at",
        "posts",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'published'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_posts_published_created_at",
        table_name="posts",
        postgresql_where=sa.text("status = 'published'"),
    )
    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_index("ix_posts_author_id", table_name="posts")
    op.drop_table("audit_log")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_table("authors")
    op.execute(sa.schema.DropSequence(sa.Sequence("audit_log_id_seq")))
    op.execute(sa.schema.DropSequence(sa.Sequence("comments_id_seq")))
    op.execute(sa.schema.DropSequence(sa.Sequence("posts_id_seq")))
