"""The messaging ports: stream producer/consumer, outbox access, dedupe
store — plus every result row the demos speak.

Four Protocols split the messaging world the way the engines need it:
``StreamProducer`` appends (XADD), ``StreamConsumer`` owns the consumer-
group lifecycle (XGROUP/XREADGROUP/XACK/XPENDING/XAUTOCLAIM/XRANGE),
``ProcessedEventStore`` is the idempotent consumer's processed-set, and
``OutboxAccess`` is the transactional outbox in PostgreSQL — including
the ONE-TRANSACTION business write (post + event together) that is the
pattern's whole point. The redis adapter and the PostgreSQL adapter
(``guide.data.messaging``) implement them under the optional-service
discipline; the engines in this package orchestrate them with ordered
awaits and no sleeps, so fakes at this boundary make every guarantee
testable deterministically.

Keys arrive fully formed (the family discipline): the engines spell
every stream key and set key in exactly one place, and the adapters
never invent one.
"""

from collections.abc import Sequence
from typing import Annotated, Final, Literal, Protocol, runtime_checkable

from pydantic import Field

from guide.core.serialization import CamelModel

NAMESPACE: Final = "guide_demo:msg:"
"""The messaging demos' key namespace root — the topic owns it exclusively."""

NAMESPACE_DISPLAY: Final = "guide_demo:msg:*"
"""The namespace as the demo payloads display it (the playground's convention)."""

ConsumeMode = Literal["healthy", "poison"]
"""The stream lab's two consumers: one acks, one deliberately does not."""

EVENT_NOTE_TYPE: Final = "demo.note"
"""The stream lab's event type — a produced note the group consumes."""

NOTE_MAX_LENGTH: Final = 80
"""The produce panel's note cap — display rows, not a document store."""

CONSUME_COUNT_MIN: Final = 1
CONSUME_COUNT_MAX: Final = 10
CONSUME_COUNT_DEFAULT: Final = 3
"""One consume round's read bound: a window, never the whole stream."""

PENDING_LIMIT: Final = 20
"""The pending list's display cap — XPENDING's range form is bounded."""

RECLAIM_COUNT: Final = 10
"""One XAUTOCLAIM round's claim bound."""

MIN_IDLE_MS_DEFAULT: Final = 1_000
MIN_IDLE_MS_MAX: Final = 60_000
"""The reclaim threshold: the demo's visibility timeout, one second by
default so the live tour needs no patience; zero claims everything."""

RELAY_BATCH_MIN: Final = 1
RELAY_BATCH_MAX: Final = 10
RELAY_BATCH_DEFAULT: Final = 5
"""One relay cycle's poll bound — the outbox is drained in batches."""

PANEL_ENTRY_LIMIT: Final = 20
"""How many trailing stream entries the roster payloads display."""


# ── Stream rows ──────────────────────────────────────────────────────────────


class EventDraft(CamelModel):
    """One event about to be appended to a stream — the producer's unit.

    ``payload`` is the canonical JSON STRING (sorted keys): the bytes a
    consumer receives are the bytes the producer sent, and the stream
    never interprets them.
    """

    event_id: str
    event_type: str
    payload: str


class StreamEntryRow(CamelModel):
    """One entry in a stream: the broker's id plus the event it carries.

    ``id`` is the XADD id (``<ms>-<seq>``) — monotonic, time-bearing, and
    the unit of acknowledgement; ``event_id`` is the logical id consumers
    dedupe on, stable across redelivery.
    """

    id: str
    event_id: str
    event_type: str
    payload: str


class PendingRow(CamelModel):
    """One PEL entry: delivered, owned, not yet acknowledged."""

    entry_id: str
    consumer: str
    idle_ms: int
    deliveries: int


class ProduceRow(CamelModel):
    """One append: the event id minted, the entry id the stream answered."""

    stream: str
    event_id: str
    entry_id: str
    note: str
    length: int
    detail: str


class ConsumeRow(CamelModel):
    """One consumer-group read: what was delivered, what was acknowledged."""

    stream: str
    group: str
    consumer: str
    mode: ConsumeMode
    delivered: list[StreamEntryRow]
    acked: int
    detail: str


class PendingListRow(CamelModel):
    """The group's pending entries list (XPENDING's honest answer)."""

    stream: str
    group: str
    entries: list[PendingRow]
    detail: str


class ReclaimRow(CamelModel):
    """One XAUTOCLAIM round: stale entries moved to the healthy consumer."""

    stream: str
    group: str
    consumer: str
    min_idle_ms: int
    claimed: list[StreamEntryRow]
    acked: int
    detail: str


class StreamPanelRow(CamelModel):
    """The stream lab's state panel: the log, in order, with its backlog."""

    stream: str
    group: str
    healthy_consumer: str
    poison_consumer: str
    length: int
    last_id: str | None
    entries: list[StreamEntryRow]
    pending_count: int


# ── Outbox rows ──────────────────────────────────────────────────────────────


class OutboxPostDraft(CamelModel):
    """The business write's body — the post the outbox event describes.

    Constraints mirror the posts table's CHECKs (title 1–120): an invalid
    draft cannot be constructed, so the one-transaction write can never be
    poisoned from the edge.
    """

    title: Annotated[str, Field(min_length=1, max_length=120)]
    body: Annotated[str, Field(max_length=5000)] = ""


class OutboxPostRow(CamelModel):
    """The committed post half of the dual write."""

    id: int
    slug: str
    title: str
    author: str
    created_at: str


class OutboxRow(CamelModel):
    """One outbox row: the event, its aggregate, its publication state.

    ``published_at`` is None until a relay cycle has delivered it AND
    survived to mark it — the crash window leaves it None on purpose.
    """

    event_id: str
    event_type: str
    aggregate: str
    payload: str
    created_at: str
    published_at: str | None


class OutboxWriteRow(CamelModel):
    """One business write through the outbox — both halves, or neither.

    ``committed`` False only on the deliberately tripped crash point (the
    atomicity proof): the transaction rolled back and NO half survived —
    ``post``/``event`` are None and ``failure`` carries PostgreSQL's own
    words for why.
    """

    committed: bool
    post: OutboxPostRow | None
    event: OutboxRow | None
    failure: str | None
    detail: str


class PublishedEntryRow(CamelModel):
    """One publish inside a relay cycle: which event landed on which id."""

    event_id: str
    entry_id: str
    aggregate: str


class RelayRow(CamelModel):
    """One relay cycle: poll unpublished → publish → mark (or crash first).

    ``crashed`` True is the simulated death between publish and mark: the
    stream carries the event, the row stays unpublished, the next cycle
    will publish it again — at-least-once made visible.
    """

    cycle: int
    stream: str
    discovered: int
    published: list[PublishedEntryRow]
    marked: int
    crashed: bool
    detail: str


class DedupeWalk(CamelModel):
    """One idempotent-consumer walk: first sightings vs duplicates."""

    processed: list[str]
    skipped_duplicates: list[str]


class OutboxConsumeRow(CamelModel):
    """The outbox stream seen through the idempotent consumer's counts."""

    stream: str
    entries: int
    processed: int
    skipped_duplicates: int
    proof: str


class OutboxStatsRow(CamelModel):
    """The outbox table's three counts — the relay's world in one row."""

    total: int
    published: int
    unpublished: int


class OutboxTelemetryRow(CamelModel):
    """The outbox demo's in-process counters, snapshot at one round's end."""

    creates: int
    relay_cycles: int
    crash_simulations: int
    publishes: int
    events_processed: int
    duplicates_skipped: int


class OutboxPanelRow(CamelModel):
    """The outbox demo's state panel: table counts, rows, stream, counters."""

    stream: str
    table: str
    stats: OutboxStatsRow
    outbox: list[OutboxRow]
    stream_entries: list[StreamEntryRow]
    telemetry: OutboxTelemetryRow


# ── Request bodies (the routers parse these; bounds are the contract) ───────


class ProduceRequest(CamelModel):
    """The produce button's body: the note the event carries."""

    note: Annotated[str, Field(max_length=NOTE_MAX_LENGTH)] = "hello, stream"


class ConsumeRequest(CamelModel):
    """The consume button's body: which consumer persona, how many entries."""

    mode: ConsumeMode = "healthy"
    count: Annotated[
        int, Field(default=CONSUME_COUNT_DEFAULT, ge=CONSUME_COUNT_MIN, le=CONSUME_COUNT_MAX)
    ] = CONSUME_COUNT_DEFAULT


class ReclaimRequest(CamelModel):
    """The reclaim button's body: the visibility timeout to enforce.

    ``min_idle_ms`` is how long a pending entry must have sat unacknowledged
    before XAUTOCLAIM will move it — the demo's stand-in for a worker's
    lease; 0 claims everything pending regardless of age.
    """

    min_idle_ms: Annotated[
        int, Field(default=MIN_IDLE_MS_DEFAULT, ge=0, le=MIN_IDLE_MS_MAX)
    ] = MIN_IDLE_MS_DEFAULT


class RelayRequest(CamelModel):
    """The relay button's body: batch size, and whether to die before marking."""

    crash_before_mark: bool = False
    batch: Annotated[
        int, Field(default=RELAY_BATCH_DEFAULT, ge=RELAY_BATCH_MIN, le=RELAY_BATCH_MAX)
    ] = RELAY_BATCH_DEFAULT


# ── The ports ────────────────────────────────────────────────────────────────


@runtime_checkable
class StreamProducer(Protocol):
    """Append events to a stream — XADD behind whatever implements this."""

    async def append(self, stream: str, draft: EventDraft) -> str:
        """Append one event; answer the stream's entry id for it."""
        ...


@runtime_checkable
class StreamConsumer(Protocol):
    """The consumer-group lifecycle over a stream — the log's read side."""

    async def ensure_group(self, stream: str, group: str) -> None:
        """Create the group idempotently (an existing group is not an error)."""
        ...

    async def read_new(
        self, stream: str, group: str, consumer: str, count: int
    ) -> list[StreamEntryRow]:
        """Deliver entries never delivered to this group (XREADGROUP ``>``)."""
        ...

    async def ack(self, stream: str, group: str, entry_ids: Sequence[str]) -> int:
        """Acknowledge delivered entries; answer how many left the PEL."""
        ...

    async def pending(self, stream: str, group: str, count: int) -> list[PendingRow]:
        """The group's pending entries list (idle time, delivery counts)."""
        ...

    async def claim(
        self, stream: str, group: str, consumer: str, min_idle_ms: int, count: int
    ) -> list[StreamEntryRow]:
        """Reclaim pending entries idle past ``min_idle_ms`` (XAUTOCLAIM)."""
        ...

    async def entries(self, stream: str) -> list[StreamEntryRow]:
        """The whole log in id order (XRANGE) — replay is the log's promise."""
        ...


@runtime_checkable
class ProcessedEventStore(Protocol):
    """The idempotent consumer's processed-set — event ids already handled."""

    async def seen(self, set_key: str, event_id: str) -> bool:
        """True when ``event_id`` was already processed (the set remembers)."""
        ...

    async def remember(self, set_key: str, event_id: str) -> None:
        """Record ``event_id`` as processed — AFTER the work, not before."""
        ...


@runtime_checkable
class OutboxAccess(Protocol):
    """The transactional outbox in PostgreSQL — writes, polls, marks.

    ``create_post_with_event`` is the pattern itself: the post and its
    event commit in ONE transaction or neither does. ``trip_crash_point``
    is the atomicity PROOF, not a feature — it makes the same transaction
    fail after both inserts (a deliberate CHECK violation) so callers can
    watch both halves vanish together.
    """

    async def create_post_with_event(
        self, draft: OutboxPostDraft, *, trip_crash_point: bool = False
    ) -> OutboxWriteRow:
        """Insert post + outbox event in one transaction; both or neither."""
        ...

    async def unpublished(self, limit: int) -> list[OutboxRow]:
        """The relay's work queue: unpublished rows, insertion order."""
        ...

    async def mark_published(self, event_ids: Sequence[str]) -> int:
        """Stamp ``published_at`` on the named events; answer how many."""
        ...

    async def recent(self, limit: int) -> list[OutboxRow]:
        """The newest outbox rows (published or not) — the panel's table."""
        ...

    async def stats(self) -> OutboxStatsRow:
        """total / published / unpublished over the whole table."""
        ...
