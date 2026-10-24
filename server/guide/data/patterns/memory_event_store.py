"""The ``EventStore`` port's process-memory adapter: append, read, conflict.

The first implementation behind ``guide.domain.patterns.event_store.
EventStore``, playing the role ``InMemoryPostRepository`` played for the
posts port: the honest in-process adapter the composition root wires
where a durable one (a PostgreSQL table with a unique ``(stream,
version)`` key — the shape the outbox table in migration 0004 already
carries) would go in production. Everything the port promises is real
here: appends stamp dense per-stream versions; the optimistic-
concurrency check runs BEFORE any event is minted, so a
``VersionConflict`` means literally nothing was appended; and both
reads return copies, so no caller can mutate history through them.

The adapter owns identity and time (the port's contract): event ids
are minted uuid4 hex, ``occurred_at`` comes from the injected clock —
defaulting to real UTC ISO-8601 stamps, overridden with a counter by
the tests and the demo so whole histories read deterministically.
"""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import final
from uuid import uuid4

from guide.domain.patterns.event_store import (
    EXPECT_EMPTY,
    EventDraft,
    StoredEvent,
    VersionConflict,
)

EventStoreClock = Callable[[], str]
"""One timestamp token per appended event; injected at construction."""


def _default_clock() -> str:
    """The production default: real UTC ISO-8601 stamps, newest-last."""
    return datetime.now(UTC).isoformat()


@final
class InMemoryEventStore:
    """Append-only facts in process memory, behind the domain port.

    Two dict-shaped truths: ``_log`` is every event in append order (the
    global history), ``_streams`` indexes the same events per stream in
    version order. Appends mint identity and position; readers get
    copies; the version check guards the write. Nothing else exists —
    an event store is the simplest durable thing there is, and the
    pattern's weight lives in the fold, not here.
    """

    def __init__(self, clock: EventStoreClock = _default_clock) -> None:
        """Hold the clock and start with an empty history."""
        self._clock = clock
        self._log: list[StoredEvent] = []
        self._streams: dict[str, list[StoredEvent]] = {}

    def append(
        self, stream: str, events: Sequence[EventDraft], expected_version: int
    ) -> list[StoredEvent]:
        """Append at the stated version — or refuse with ``VersionConflict``.

        The check is first and total: if the stream is not at exactly
        ``expected_version`` (``EXPECT_EMPTY`` for a stream that must
        not exist yet), NO event from this call is stored — the failed
        writer cannot leave half a batch behind.
        """
        current = len(self._streams.get(stream, ()))
        believed_empty = expected_version == EXPECT_EMPTY
        if (believed_empty and current != 0) or (
            not believed_empty and expected_version != current
        ):
            raise VersionConflict(stream=stream, expected=expected_version, actual=current)
        minted = [
            StoredEvent(
                event_id=uuid4().hex,
                stream=stream,
                event_type=draft.event_type,
                payload=dict(draft.payload),
                version=current + position,
                occurred_at=self._clock(),
            )
            for position, draft in enumerate(events, start=1)
        ]
        self._streams.setdefault(stream, []).extend(minted)
        self._log.extend(minted)
        return minted

    def stream(self, stream_id: str) -> list[StoredEvent]:
        """One stream's events in version order; empty for an unknown id."""
        return list(self._streams.get(stream_id, ()))

    def log(self) -> list[StoredEvent]:
        """Every event across streams, append order — the foldable history."""
        return list(self._log)
