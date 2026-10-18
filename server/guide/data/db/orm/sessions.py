"""The async session factory: units of work beside the engine.

One factory per process (built at the composition root right after the
engine), many short-lived sessions drawn from it. A session is the
unit of work — it IS the transaction boundary, the identity map, and
the dirty-checking engine at once; opening one per request-sized piece
of work and letting the context manager commit-or-rollback on exit is
the whole discipline. ``expire_on_commit=False`` keeps committed
objects readable without a refresh SELECT, which matters in async code
where a surprise lazy load is an error, not a pause (see the probe's
``awaitable_attrs`` usage).
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the process's session factory over the shared engine.

    The factory is called without arguments — ``sessions()`` — and
    yields an ``AsyncSession`` whose context manager commits on normal
    exit and rolls back on any exception, so no code path leaks a
    transaction. Sessions are cheap; transactions are not.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
