"""Engine-level SQL instrumentation: capture what actually runs.

Every claim this topic makes about query counts is a MEASUREMENT taken
through this module: one SQLAlchemy event listener on the engine's sync
facade, attached for the duration of a probe and removed after. The
``before_cursor_execute`` hook fires exactly once per statement the
dialect sends — including the SELECTs lazy loading emits mid-iteration
— so a strategy's ``sql_count`` is the count the database saw, not a
narrative. Attach/detach is symmetric and scoped (``record_sql`` is a
context manager), so two probes can never count each other's
statements.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


class SqlRecorder:
    """The statements one engine emitted while a probe ran."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def count(self, verb: str | None = None) -> int:
        """How many statements ran (optionally only one leading verb)."""
        if verb is None:
            return len(self.statements)
        return sum(1 for statement in self.statements if _verb_of(statement) == verb)

    def with_verb(self, verb: str) -> list[str]:
        """Every captured statement with the given leading verb."""
        return [statement for statement in self.statements if _verb_of(statement) == verb]


def _verb_of(statement: str) -> str:
    """The statement's leading SQL verb, uppercased (SELECT/UPDATE/...)."""
    return statement.strip().split(None, 1)[0].upper() if statement.strip() else ""


@contextmanager
def record_sql(engine: AsyncEngine) -> Iterator[SqlRecorder]:
    """Attach a recorder to the engine for the block's duration, no longer.

    The listener lives on the engine's SYNCHRONOUS facade (async wraps
    sync in SQLAlchemy; every await eventually crosses it), which is why
    an ``AsyncEngine`` is accepted and ``engine.sync_engine`` is what
    listens.
    """
    recorder = SqlRecorder()

    def before_cursor_execute(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        recorder.statements.append(statement)

    sync_engine = engine.sync_engine
    event.listen(sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield recorder
    finally:
        event.remove(sync_engine, "before_cursor_execute", before_cursor_execute)
