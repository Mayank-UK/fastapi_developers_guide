"""PgSchemaReader — live introspection through information_schema + pg_catalog.

The explorer demo's adapter: five read-only queries, one connection,
one ``SchemaSnapshot``. Nothing here is hard-coded — the payload the
demo serves is whatever PostgreSQL actually reports, so the migration's
tables, constraints, and indexes can be watched appearing on the real
server. information_schema answers the standard questions (tables,
columns); pg_catalog answers the PostgreSQL-specific ones (foreign-key
ON DELETE behavior, CHECK definitions, index kind and partial WHERE)
because the standard schema does not carry them.

Unreachable/unusable PostgreSQL maps to the taxonomy's
``service_unavailable`` envelope — the optional-service discipline:
the app stays up, the demo reports honestly why it cannot.
"""

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine

from guide.core.errors import AppError, FailureKind
from guide.domain.db.ports import (
    CheckRow,
    ColumnRow,
    ForeignKeyRow,
    IndexRow,
    SchemaSnapshot,
)

logger = structlog.get_logger()

_DATABASE_QUERY = """
SELECT current_database()
"""

_TABLES_QUERY = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
"""

_COLUMNS_QUERY = """
SELECT table_name, column_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position
"""

_FOREIGN_KEYS_QUERY = """
SELECT c.conname AS constraint_name,
       tn.relname AS table_name,
       fn.relname AS referenced_table,
       c.confdeltype AS on_delete_code,
       (SELECT string_agg(a.attname, ', ' ORDER BY x.ord)
          FROM unnest(c.conkey) WITH ORDINALITY AS x(attnum, ord)
          JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = x.attnum
       ) AS fk_columns,
       (SELECT string_agg(a.attname, ', ' ORDER BY x.ord)
          FROM unnest(c.confkey) WITH ORDINALITY AS x(attnum, ord)
          JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = x.attnum
       ) AS fk_ref_columns
FROM pg_constraint c
JOIN pg_class tn ON tn.oid = c.conrelid
JOIN pg_namespace n ON n.oid = tn.relnamespace
JOIN pg_class fn ON fn.oid = c.confrelid
WHERE c.contype = 'f' AND n.nspname = 'public'
ORDER BY tn.relname, c.conname
"""

_CHECKS_QUERY = """
SELECT c.conname AS constraint_name,
       tn.relname AS table_name,
       pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class tn ON tn.oid = c.conrelid
JOIN pg_namespace n ON n.oid = tn.relnamespace
WHERE c.contype = 'c' AND n.nspname = 'public'
ORDER BY tn.relname, c.conname
"""

_INDEXES_QUERY = """
SELECT ic.relname AS index_name,
       tn.relname AS table_name,
       am.amname AS kind,
       ix.indisunique AS is_unique,
       ix.indisprimary AS is_primary,
       pg_get_expr(ix.indpred, ix.indrelid) AS where_clause,
       (SELECT string_agg(a.attname, ', ' ORDER BY x.ord)
          FROM unnest(ix.indkey) WITH ORDINALITY AS x(attnum, ord)
          JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = x.attnum
       ) AS index_columns
FROM pg_index ix
JOIN pg_class ic ON ic.oid = ix.indexrelid
JOIN pg_class tn ON tn.oid = ix.indrelid
JOIN pg_namespace n ON n.oid = tn.relnamespace
JOIN pg_am am ON am.oid = ic.relam
WHERE n.nspname = 'public'
ORDER BY tn.relname, ic.relname
"""

_ON_DELETE_BY_CODE: dict[str, str] = {
    "a": "NO ACTION",
    "r": "RESTRICT",
    "c": "CASCADE",
    "n": "SET NULL",
    "d": "SET DEFAULT",
}
"""pg_constraint's confdeltype codes → the SQL spellings people read."""


def _char(value: str | bytes) -> str:
    """Normalize PostgreSQL's ``"char"`` type: asyncpg hands it over as bytes."""
    return value.decode() if isinstance(value, bytes) else value


class PgSchemaReader:
    """Reads the live public schema into one ``SchemaSnapshot``."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def read(self) -> SchemaSnapshot:
        """Harvest every fact in one connection; map failures to 503."""
        try:
            async with self._engine.connect() as connection:
                database_name = (await connection.execute(sa.text(_DATABASE_QUERY))).scalar_one()
                table_names = [
                    row[0] for row in (await connection.execute(sa.text(_TABLES_QUERY))).all()
                ]
                columns = [
                    ColumnRow(
                        table_name=row.table_name,
                        column_name=row.column_name,
                        data_type=row.data_type,
                        udt_name=row.udt_name,
                        is_nullable=row.is_nullable == "YES",
                        column_default=row.column_default,
                    )
                    for row in (await connection.execute(sa.text(_COLUMNS_QUERY))).all()
                ]
                foreign_keys = [
                    ForeignKeyRow(
                        constraint_name=row.constraint_name,
                        table_name=row.table_name,
                        columns=row.fk_columns.split(", "),
                        referenced_table=row.referenced_table,
                        referenced_columns=row.fk_ref_columns.split(", "),
                        on_delete=_ON_DELETE_BY_CODE.get(_char(row.on_delete_code), "NO ACTION"),
                    )
                    for row in (await connection.execute(sa.text(_FOREIGN_KEYS_QUERY))).all()
                ]
                checks = [
                    CheckRow(
                        constraint_name=row.constraint_name,
                        table_name=row.table_name,
                        definition=row.definition,
                    )
                    for row in (await connection.execute(sa.text(_CHECKS_QUERY))).all()
                ]
                indexes = [
                    IndexRow(
                        index_name=row.index_name,
                        table_name=row.table_name,
                        columns=row.index_columns.split(", "),
                        kind=row.kind,
                        is_unique=row.is_unique,
                        is_primary=row.is_primary,
                        where=row.where_clause,
                    )
                    for row in (await connection.execute(sa.text(_INDEXES_QUERY))).all()
                ]
        except (sa.exc.SQLAlchemyError, OSError) as exc:
            logger.warning(
                "schema_introspection_unavailable",
                error=type(exc).__name__,
                detail=str(exc),
            )
            raise AppError(
                FailureKind.SERVICE_UNAVAILABLE,
                "PostgreSQL is unreachable or unreadable — the schema explorer "
                "introspects the live database and refuses to serve stale facts.",
            ) from exc
        return SchemaSnapshot(
            database_name=database_name,
            tables=table_names,
            columns=columns,
            foreign_keys=foreign_keys,
            checks=checks,
            indexes=indexes,
        )
