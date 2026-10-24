"""The event store: append-only facts, and state folded back out of them.

Event sourcing inverts the usual storage question. A mutable row answers
"what is the current state?"; an event stream answers "what HAPPENED?"
and derives the current state by replaying the history. The store itself
is deliberately the smaller half of the pattern: it only appends —
facts go in with a dense per-stream version, and nothing ever rewrites
or deletes one. All the semantics live in the FOLD: a pure left-fold
over an ordered history where each event type has one handler that maps
(state, event) -> next state. Because the fold is pure, replaying the
same events always rebuilds the same state — the property that makes
projections, rebuilds, and after-the-fact audit views cheap.

Two invariants do the concurrency work, both borrowed from the classic
event-store literature (Greg Young's formulation): dense per-stream
versions (1, 2, 3… — positions in the stream, not timestamps) and
OPTIMISTIC concurrency on append — the writer states which version it
believes the stream is at, and the store refuses the write when the
stream moved on underneath it (``VersionConflict``). No locks, no
blocking: a lost race is told it lost. The demo in the advanced-
architecture topic drives exactly those two invariants.

This module is the domain half: the ``StoredEvent`` fact, the
``EventStore`` port (a Protocol, like every port in this repo), the
``EventDraft`` a writer submits, the conflict error, and the pure
``fold_stream`` engine. The process-memory adapter lives in
``guide.data.patterns.memory_event_store`` — the same port/adapter
split the posts area pioneered.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

Clock = Callable[[], str]
"""One timestamp token per append — an ISO-8601 string by convention.
Injected at the adapter, so tests and demos make time deterministic
(the same discipline the circuit breaker's monotonic clock follows)."""

EXPECT_EMPTY: int = -1
"""The ``expected_version`` that means "this stream must not exist yet" —
the classic event-store convention (no magic 0: version 0 is never used,
the first event is version 1)."""

State = dict[str, object]
"""A folded aggregate's state: string keys, JSON-shaped values — the
same shape a projection or a wire payload carries."""

EventHandler = Callable[[State, "StoredEvent"], State]
"""One event type's fold rule: pure — returns the NEXT state, mutates
nothing. Handlers that mutate their input break replay; the demo's
handlers copy-on-write for exactly this reason."""


class VersionConflict(Exception):
    """An append lost the optimistic-concurrency race; message names both versions."""

    def __init__(self, stream: str, expected: int, actual: int) -> None:
        super().__init__(
            f"stream {stream!r} is at version {actual}, but the writer "
            f"expected {expected} — the stream moved on; re-read, re-fold, retry"
        )
        self.stream = stream
        self.expected = expected
        self.actual = actual


class UnknownEventTypeError(Exception):
    """The fold met an event type with no handler — an unreadable log must
    fail loudly, never drop facts silently."""


@dataclass(frozen=True, slots=True)
class EventDraft:
    """What a writer submits: the fact's type and data, nothing else.

    The store mints identity (event id), position (version), and time
    (``occurred_at``) — a writer cannot forge any of the three.
    """

    event_type: str
    payload: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StoredEvent:
    """One immutable fact, as stored: the draft plus the store's stamps.

    ``version`` is the event's dense position in ITS stream (1-based);
    ``occurred_at`` is the clock token the adapter was holding when the
    fact was appended. Frozen: a stored fact never changes after this.
    """

    event_id: str
    stream: str
    event_type: str
    payload: Mapping[str, object]
    version: int
    occurred_at: str


@runtime_checkable
class EventStore(Protocol):
    """The port every event-store adapter implements (append + read).

    ``append`` is the ONLY write, and it is optimistic: the caller states
    the version it believes the stream is at (``EXPECT_EMPTY`` for a new
    stream); a stale belief raises ``VersionConflict`` and appends
    nothing. ``stream`` returns one stream's events in version order;
    ``log`` returns every event across streams in append order — the
    full history a rebuild or an audit projection folds over.
    """

    def append(
        self, stream: str, events: Sequence[EventDraft], expected_version: int
    ) -> list[StoredEvent]:
        """Append facts to one stream at the stated version, or conflict."""
        ...

    def stream(self, stream_id: str) -> list[StoredEvent]:
        """One stream's events, version order (empty list for an unknown id)."""
        ...

    def log(self) -> list[StoredEvent]:
        """Every stored event across all streams, append order."""
        ...


def fold_stream(
    history: Sequence[StoredEvent],
    initial: Mapping[str, object],
    handlers: Mapping[str, EventHandler],
) -> State:
    """Fold a history into state: apply each event, in order, to the last.

    The left fold that IS event sourcing's read side: start from
    ``initial`` (the empty aggregate), walk the stream's facts in
    version order, and let each fact's handler produce the next state.
    Purity is the contract — handlers receive state and return the next
    state without mutating their input — so folding the same history
    twice yields the same answer, today and after a restart. An event
    type with no handler raises ``UnknownEventTypeError``: a log you
    cannot fully read is a defect, not a skip.
    """
    state: State = dict(initial)
    for event in history:
        handler = handlers.get(event.event_type)
        if handler is None:
            raise UnknownEventTypeError(
                f"no handler for event type {event.event_type!r} (event "
                f"{event.event_id!r}, version {event.version})"
            )
        state = handler(state, event)
    return state
