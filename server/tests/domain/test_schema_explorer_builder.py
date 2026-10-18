"""Schema-explorer builder tests: shaping fixture rows, no database.

The builder is pure — these tests pin its contract against a hand-built
``SchemaSnapshot`` that mirrors a slice of the real guide schema: array
type display, partial-index WHERE, FK drill-down, honest ``None`` for a
table the snapshot does not contain.
"""

from guide.domain.db.ports import (
    CheckRow,
    ColumnRow,
    ForeignKeyRow,
    IndexRow,
    SchemaSnapshot,
)
from guide.domain.demos.schema_explorer import (
    build_schema_explorer,
    build_table_detail,
    build_table_summary,
)


def a_snapshot() -> SchemaSnapshot:
    """A two-table snapshot shaped like the real guide schema's slice."""
    return SchemaSnapshot(
        database_name="guide",
        tables=["authors", "posts"],
        columns=[
            ColumnRow(
                table_name="authors",
                column_name="id",
                data_type="uuid",
                udt_name="uuid",
                is_nullable=False,
                column_default="gen_random_uuid()",
            ),
            ColumnRow(
                table_name="posts",
                column_name="id",
                data_type="bigint",
                udt_name="int8",
                is_nullable=False,
                column_default="nextval('posts_id_seq'::regclass)",
            ),
            ColumnRow(
                table_name="posts",
                column_name="tags",
                data_type="ARRAY",
                udt_name="_text",
                is_nullable=False,
                column_default="'{}'::text[]",
            ),
            ColumnRow(
                table_name="posts",
                column_name="title",
                data_type="text",
                udt_name="text",
                is_nullable=False,
                column_default=None,
            ),
        ],
        foreign_keys=[
            ForeignKeyRow(
                constraint_name="fk_posts_author_id_authors",
                table_name="posts",
                columns=["author_id"],
                referenced_table="authors",
                referenced_columns=["id"],
                on_delete="RESTRICT",
            )
        ],
        checks=[
            CheckRow(
                constraint_name="ck_posts_status_domain",
                table_name="posts",
                definition="CHECK ((status)::text = ANY ((ARRAY['draft'::character varying, "
                "'published'::character varying])::text[]))",
            )
        ],
        indexes=[
            IndexRow(
                index_name="pk_posts",
                table_name="posts",
                columns=["id"],
                kind="btree",
                is_unique=True,
                is_primary=True,
                where=None,
            ),
            IndexRow(
                index_name="ix_posts_published_created_at",
                table_name="posts",
                columns=["created_at"],
                kind="btree",
                is_unique=False,
                is_primary=False,
                where="(status = 'published'::text)",
            ),
            IndexRow(
                index_name="uq_posts_slug",
                table_name="posts",
                columns=["slug"],
                kind="btree",
                is_unique=True,
                is_primary=False,
                where=None,
            ),
        ],
    )


def test_root_payload_lists_every_table_with_fact_counts() -> None:
    payload = build_schema_explorer(a_snapshot(), focus=None)
    assert payload.database_name == "guide"
    assert payload.table_count == 2
    assert [t.name for t in payload.tables] == ["authors", "posts"]
    posts = payload.tables[1]
    assert (posts.column_count, posts.foreign_key_count, posts.check_count) == (3, 1, 1)
    assert posts.index_count == 3
    assert payload.focus is None


def test_focus_drills_into_one_table_with_full_anatomy() -> None:
    payload = build_schema_explorer(a_snapshot(), focus="posts")
    focus = payload.focus
    assert focus is not None
    assert focus.name == "posts"
    by_name = {c.name: c for c in focus.columns}
    assert by_name["id"].default == "nextval('posts_id_seq'::regclass)"
    assert by_name["id"].nullable is False
    assert by_name["title"].default is None
    # ARRAY + udt_name '_text' displays as the element type plus brackets.
    assert by_name["tags"].type == "text[]"
    assert focus.primary_key == ["id"]
    assert focus.foreign_keys[0].on_delete == "RESTRICT"
    assert focus.foreign_keys[0].references_table == "authors"
    assert focus.checks[0].name == "ck_posts_status_domain"
    partial = next(i for i in focus.indexes if not i.unique)
    assert partial.where == "(status = 'published'::text)"
    assert {i.name for i in focus.indexes} == {
        "pk_posts",
        "ix_posts_published_created_at",
        "uq_posts_slug",
    }


def test_focus_on_an_unknown_table_is_none_and_summary_still_counts() -> None:
    snapshot = a_snapshot()
    assert build_table_detail(snapshot, "nope") is None
    payload = build_schema_explorer(snapshot, focus="nope")
    assert payload.focus is None
    assert payload.table_count == 2


def test_summary_and_detail_agree_on_counts() -> None:
    snapshot = a_snapshot()
    detail = build_table_detail(snapshot, "posts")
    assert detail is not None
    summary = build_table_summary(snapshot, "posts")
    assert len(detail.columns) == summary.column_count
    assert len(detail.foreign_keys) == summary.foreign_key_count
    assert len(detail.checks) == summary.check_count
    assert len(detail.indexes) == summary.index_count


def test_empty_schema_is_an_honest_empty_roster() -> None:
    empty = SchemaSnapshot(
        database_name="guide",
        tables=[],
        columns=[],
        foreign_keys=[],
        checks=[],
        indexes=[],
    )
    payload = build_schema_explorer(empty, focus=None)
    assert payload.table_count == 0
    assert payload.tables == []
    assert payload.focus is None
