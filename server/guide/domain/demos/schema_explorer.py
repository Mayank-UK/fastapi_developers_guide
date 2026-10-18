"""Schema-explorer demo payloads: the live database, shaped for reading.

``GET /api/demo/db/schema-explorer`` serves these payloads — topic 16's
first demo. The wire contract is two views of one harvest: the ROOT
lists every public table with its fact counts (columns, FKs, checks,
indexes); ``?table=posts`` drills into ONE table and gets ``focus`` —
every column with type/nullable/default, the primary key, FKs with
their ON DELETE behavior, CHECK definitions verbatim, and every index
with kind/uniqueness/partial WHERE. Nothing is hard-coded: the builder
receives the ``SchemaSnapshot`` the adapter just read from the live
database, so a new migration visibly changes the demo's answer.

The builder is PURE — it shapes rows, it never queries (the same
discipline as every builder in this package). Asking for a table the
snapshot does not contain yields ``focus=None``; the ROUTER turns that
into the honest 404 envelope.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import SchemaSnapshot


class TableSummaryCard(CamelModel):
    """One table as the root view lists it: a name plus its fact counts."""

    name: str
    column_count: int
    foreign_key_count: int
    check_count: int
    index_count: int


class ColumnCard(CamelModel):
    """One column: type as PostgreSQL spells it, nullability, raw default."""

    name: str
    type: str
    nullable: bool
    default: str | None


class ForeignKeyCard(CamelModel):
    """One foreign key: local columns → referenced columns, ON DELETE."""

    name: str
    columns: list[str]
    references_table: str
    references_columns: list[str]
    on_delete: str


class CheckCard(CamelModel):
    """One CHECK constraint, definition exactly as pg_get_constraintdef."""

    name: str
    definition: str


class IndexCard(CamelModel):
    """One index: columns, access method, uniqueness, primary-ness, WHERE."""

    name: str
    columns: list[str]
    kind: str
    unique: bool
    primary: bool
    where: str | None


class TableDetailCard(CamelModel):
    """The drill-down: one table's full introspected anatomy."""

    name: str
    columns: list[ColumnCard]
    primary_key: list[str]
    foreign_keys: list[ForeignKeyCard]
    checks: list[CheckCard]
    indexes: list[IndexCard]


class SchemaExplorerPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/schema-explorer``."""

    database_name: str
    table_count: int
    tables: list[TableSummaryCard]
    focus: TableDetailCard | None
    reasoning: str


def _display_type(data_type: str, udt_name: str) -> str:
    """information_schema's two type fields, merged into what PG prints.

    Arrays arrive as ``data_type='ARRAY'`` + ``udt_name='_text'`` — the
    leading underscore IS PostgreSQL's array marker in pg_type, so the
    honest display is the element type plus ``[]``.
    """
    if data_type == "ARRAY" and udt_name.startswith("_"):
        return f"{udt_name[1:]}[]"
    return data_type


def build_table_summary(snapshot: SchemaSnapshot, table_name: str) -> TableSummaryCard:
    """Count one table's facts from the snapshot (pure)."""
    return TableSummaryCard(
        name=table_name,
        column_count=sum(1 for c in snapshot.columns if c.table_name == table_name),
        foreign_key_count=sum(1 for f in snapshot.foreign_keys if f.table_name == table_name),
        check_count=sum(1 for c in snapshot.checks if c.table_name == table_name),
        index_count=sum(1 for i in snapshot.indexes if i.table_name == table_name),
    )


def build_table_detail(snapshot: SchemaSnapshot, table_name: str) -> TableDetailCard | None:
    """Assemble one table's drill-down; None when the table does not exist."""
    if table_name not in snapshot.tables:
        return None
    primary_key = [
        index.columns
        for index in snapshot.indexes
        if index.table_name == table_name and index.is_primary
    ]
    return TableDetailCard(
        name=table_name,
        columns=[
            ColumnCard(
                name=c.column_name,
                type=_display_type(c.data_type, c.udt_name),
                nullable=c.is_nullable,
                default=c.column_default,
            )
            for c in snapshot.columns
            if c.table_name == table_name
        ],
        primary_key=primary_key[0] if primary_key else [],
        foreign_keys=[
            ForeignKeyCard(
                name=f.constraint_name,
                columns=f.columns,
                references_table=f.referenced_table,
                references_columns=f.referenced_columns,
                on_delete=f.on_delete,
            )
            for f in snapshot.foreign_keys
            if f.table_name == table_name
        ],
        checks=[
            CheckCard(name=c.constraint_name, definition=c.definition)
            for c in snapshot.checks
            if c.table_name == table_name
        ],
        indexes=[
            IndexCard(
                name=i.index_name,
                columns=i.columns,
                kind=i.kind,
                unique=i.is_unique,
                primary=i.is_primary,
                where=i.where,
            )
            for i in snapshot.indexes
            if i.table_name == table_name
        ],
    )


def build_schema_explorer(snapshot: SchemaSnapshot, focus: str | None) -> SchemaExplorerPayload:
    """Shape the explorer payload (pure): the roster, optionally one focus."""
    return SchemaExplorerPayload(
        database_name=snapshot.database_name,
        table_count=len(snapshot.tables),
        tables=[build_table_summary(snapshot, name) for name in snapshot.tables],
        focus=build_table_detail(snapshot, focus) if focus is not None else None,
        reasoning=(
            f"Introspected live from PostgreSQL database {snapshot.database_name!r} via "
            "information_schema (tables, columns) and pg_catalog (foreign keys, CHECK "
            "definitions, index kinds and partial WHERE clauses) — nothing below is "
            "hard-coded; run the next migration and this answer changes with it."
        ),
    )
