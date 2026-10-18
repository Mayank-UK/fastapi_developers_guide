"""The in-transaction audit pattern, proven against the real PostgreSQL.

The pattern's whole claim is atomicity: the audit row and the change it
describes commit together and roll back together. These tests insert
both rows on ONE connection inside ONE transaction and then commit or
abort on purpose — counting rows afterwards is the proof.
"""

import sqlalchemy as sa
from pg_url import COMPOSE_PG_URL
from sqlalchemy.ext.asyncio import create_async_engine

from guide.data.db.audit import record_audit
from guide.data.db.schema import audit_log, authors
from guide.domain.db.audit import AuditEvent, audit_row_values


def _an_event(email: str) -> AuditEvent:
    return AuditEvent(
        actor="pytest",
        action="insert",
        table_name="authors",
        row_pk=email,
        changes={"email": f"absent -> {email}"},
    )


async def test_audit_row_values_is_the_exactly_the_table_columns() -> None:
    event = _an_event("shape@guide.dev")
    assert audit_row_values(event) == {
        "actor": "pytest",
        "action": "insert",
        "table_name": "authors",
        "row_pk": "shape@guide.dev",
        "changes": {"email": "absent -> shape@guide.dev"},
    }


async def test_commit_persists_the_change_and_its_audit_row_together() -> None:
    email = "audit-commit@guide.dev"
    engine = create_async_engine(COMPOSE_PG_URL)
    try:
        async with engine.connect() as connection:
            async with connection.begin():
                await connection.execute(
                    sa.insert(authors).values(name="Ada", email=email)
                )
                await record_audit(connection, _an_event(email))
            changes = await connection.scalar(
                sa.select(sa.func.count()).select_from(authors).where(authors.c.email == email)
            )
            audits = await connection.scalar(
                sa.select(sa.func.count())
                .select_from(audit_log)
                .where(audit_log.c.row_pk == email)
            )
            assert changes == 1
            assert audits == 1
            # Server defaults did their part: the audit row carries occurred_at.
            occurred = await connection.scalar(
                sa.select(audit_log.c.occurred_at).where(audit_log.c.row_pk == email)
            )
            assert occurred is not None
    finally:
        async with engine.connect() as cleanup:
            await cleanup.execute(sa.delete(audit_log).where(audit_log.c.row_pk == email))
            await cleanup.execute(sa.delete(authors).where(authors.c.email == email))
            await cleanup.commit()
        await engine.dispose()


async def test_rollback_takes_the_change_and_its_audit_row_with_it() -> None:
    email = "audit-rollback@guide.dev"
    engine = create_async_engine(COMPOSE_PG_URL)
    try:
        async with engine.connect() as connection:
            try:
                async with connection.begin():
                    await connection.execute(
                        sa.insert(authors).values(name="Grace", email=email)
                    )
                    await record_audit(connection, _an_event(email))
                    raise RuntimeError("the business change failed after the audit write")
            except RuntimeError:
                pass
            changes = await connection.scalar(
                sa.select(sa.func.count()).select_from(authors).where(authors.c.email == email)
            )
            audits = await connection.scalar(
                sa.select(sa.func.count())
                .select_from(audit_log)
                .where(audit_log.c.row_pk == email)
            )
            assert changes == 0
            assert audits == 0
    finally:
        await engine.dispose()
