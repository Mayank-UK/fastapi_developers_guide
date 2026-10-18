"""The messaging engines over FAKES at the port boundary.

Every guarantee the demos claim is pinned here deterministically —
ordered awaits, zero sleeps: the healthy/poison consumer personas and
their pending bookkeeping, XAUTOCLAIM reclaim semantics, the outbox
relay's poll → publish → mark cycle, the crash window's guaranteed
redelivery, the idempotent walk's processed-vs-skipped counts, and the
relay lock's single-flight. The fakes below are the ports' contracts in
miniature: an append-only list with per-group delivery state, a plain
set, and an in-memory outbox whose only cleverness is honest ordering.
"""

import asyncio
from uuid import UUID

from guide.domain.db.ids import uuid7_timestamp_ms
from guide.domain.messaging.idempotence import IdempotentConsumer
from guide.domain.messaging.outbox_service import (
    OUTBOX_STREAM,
    PROCESSED_SET_KEY,
    OutboxRelayService,
)
from guide.domain.messaging.ports import (
    ConsumeRequest,
    EventDraft,
    OutboxPostDraft,
    OutboxRow,
    OutboxStatsRow,
    OutboxWriteRow,
    PendingRow,
    ProduceRequest,
    ReclaimRequest,
    RelayRequest,
    RelayRow,
    StreamEntryRow,
)
from guide.domain.messaging.stream_service import (
    GROUP,
    HEALTHY_CONSUMER,
    POISON_CONSUMER,
    STREAM_KEY,
    StreamLabService,
)


class FakeStream:
    """An in-memory stream + consumer groups: the log's contract, miniature."""

    def __init__(self) -> None:
        self.log: list[StreamEntryRow] = []
        # group -> entry-id -> (owning consumer, delivery count)
        self.pels: dict[str, dict[str, tuple[str, int]]] = {}

    async def append(self, stream: str, draft: EventDraft) -> str:
        entry_id = f"0-{len(self.log) + 1}"
        self.log.append(
            StreamEntryRow(
                id=entry_id,
                event_id=draft.event_id,
                event_type=draft.event_type,
                payload=draft.payload,
            )
        )
        return entry_id

    async def ensure_group(self, stream: str, group: str) -> None:
        self.pels.setdefault(group, {})

    async def read_new(
        self, stream: str, group: str, consumer: str, count: int
    ) -> list[StreamEntryRow]:
        pel = self.pels.setdefault(group, {})
        undelivered = [row for row in self.log if row.id not in pel][:count]
        for row in undelivered:
            pel[row.id] = (consumer, 1)
        return undelivered

    async def ack(self, stream: str, group: str, entry_ids: list[str]) -> int:
        pel = self.pels.setdefault(group, {})
        removed = sum(1 for entry_id in entry_ids if pel.pop(entry_id, None) is not None)
        return removed

    async def pending(self, stream: str, group: str, count: int) -> list[PendingRow]:
        pel = self.pels.setdefault(group, {})
        return [
            PendingRow(entry_id=entry_id, consumer=consumer, idle_ms=0, deliveries=deliveries)
            for entry_id, (consumer, deliveries) in pel.items()
        ][:count]

    async def claim(
        self, stream: str, group: str, consumer: str, min_idle_ms: int, count: int
    ) -> list[StreamEntryRow]:
        pel = self.pels.setdefault(group, {})
        # idle is always 0 in the fake: only a zero threshold claims (tests pin this).
        claimable = [row for row in self.log if row.id in pel][:count]
        claimed = []
        for row in claimable:
            _, deliveries = pel[row.id]
            pel[row.id] = (consumer, deliveries + 1)
            claimed.append(row)
        return claimed

    async def entries(self, stream: str) -> list[StreamEntryRow]:
        return list(self.log)


class FakeProcessedSet:
    """The processed-set port over one plain set."""

    def __init__(self) -> None:
        self.seen_ids: set[str] = set()

    async def seen(self, set_key: str, event_id: str) -> bool:
        return event_id in self.seen_ids

    async def remember(self, set_key: str, event_id: str) -> None:
        self.seen_ids.add(event_id)


class FakeOutbox:
    """An in-memory outbox: honest ordering, honest stamping."""

    def __init__(self) -> None:
        self.rows: list[OutboxRow] = []
        self.published: set[str] = set()
        self.posts: list[str] = []
        self._next_id = 0

    async def create_post_with_event(
        self, draft: OutboxPostDraft, *, trip_crash_point: bool = False
    ) -> OutboxWriteRow:
        if trip_crash_point:
            return OutboxWriteRow(
                committed=False,
                post=None,
                event=None,
                failure="fake: the crash point tripped",
                detail="rolled back — neither half survives",
            )
        self._next_id += 1
        self.posts.append(draft.title)
        row = OutboxRow(
            event_id=f"00000000-0000-7000-8000-{self._next_id:012d}",
            event_type="post.created",
            aggregate=f"posts:{self._next_id}",
            payload=f'{{"title": "{draft.title}"}}',
            created_at="2026-10-16T00:00:00+00:00",
            published_at=None,
        )
        self.rows.append(row)
        return OutboxWriteRow(
            committed=True,
            post=None,
            event=row,
            failure=None,
            detail="committed",
        )

    async def unpublished(self, limit: int) -> list[OutboxRow]:
        return [row for row in self.rows if row.event_id not in self.published][:limit]

    async def mark_published(self, event_ids: list[str]) -> int:
        marked = 0
        for index, row in enumerate(self.rows):
            if row.event_id in event_ids and row.event_id not in self.published:
                self.published.add(row.event_id)
                self.rows[index] = row.model_copy(
                    update={"published_at": "2026-10-16T00:00:01+00:00"}
                )
                marked += 1
        return marked

    async def recent(self, limit: int) -> list[OutboxRow]:
        return list(self.rows[-limit:])

    async def stats(self) -> OutboxStatsRow:
        return OutboxStatsRow(
            total=len(self.rows),
            published=len(self.published),
            unpublished=len(self.rows) - len(self.published),
        )


def _lab() -> tuple[StreamLabService, FakeStream]:
    stream = FakeStream()
    return StreamLabService(stream, stream), stream


def _relay() -> tuple[OutboxRelayService, FakeOutbox, FakeStream, FakeProcessedSet]:
    outbox, stream, processed = FakeOutbox(), FakeStream(), FakeProcessedSet()
    service = OutboxRelayService(outbox, stream, stream, processed)
    return service, outbox, stream, processed


# ── The stream lab engine ───────────────────────────────────────────────────


async def test_produce_appends_uuidv7_events_in_order() -> None:
    lab, stream = _lab()
    for note in ("first", "second"):
        row = await lab.produce(ProduceRequest(note=note))
        assert row.length >= 1
        assert uuid7_timestamp_ms(UUID(row.event_id)) > 0  # a real UUIDv7
    assert [row.payload for row in stream.log] == [
        '{"note": "first"}',
        '{"note": "second"}',
    ]  # canonical JSON, arrival order


async def test_healthy_consumer_reads_then_acks() -> None:
    lab, stream = _lab()
    await lab.produce(ProduceRequest())
    row = await lab.consume(ConsumeRequest(mode="healthy", count=5))
    assert row.consumer == HEALTHY_CONSUMER
    assert len(row.delivered) == 1
    assert row.acked == 1
    assert await stream.pending(STREAM_KEY, GROUP, 20) == []


async def test_poison_consumer_leaves_entries_pending_and_owned() -> None:
    lab, stream = _lab()
    await lab.produce(ProduceRequest())
    row = await lab.consume(ConsumeRequest(mode="poison", count=5))
    assert row.consumer == POISON_CONSUMER
    assert len(row.delivered) == 1
    assert row.acked == 0  # never acked — that is the persona
    pending = await stream.pending(STREAM_KEY, GROUP, 20)
    assert [(p.consumer, p.deliveries) for p in pending] == [(POISON_CONSUMER, 1)]


async def test_new_reads_never_resend_owned_pending_entries() -> None:
    lab, _ = _lab()
    await lab.produce(ProduceRequest())
    await lab.consume(ConsumeRequest(mode="poison", count=5))
    healthy = await lab.consume(ConsumeRequest(mode="healthy", count=5))
    assert healthy.delivered == []  # '>' only delivers entries NEW to the group


async def test_consume_on_an_empty_stream_reports_nothing() -> None:
    lab, _ = _lab()
    row = await lab.consume(ConsumeRequest(mode="healthy", count=5))
    assert row.delivered == [] and row.acked == 0
    assert "read nothing" in row.detail


async def test_reclaim_moves_stale_entries_and_finishes_them() -> None:
    lab, stream = _lab()
    await lab.produce(ProduceRequest())
    await lab.produce(ProduceRequest())
    await lab.consume(ConsumeRequest(mode="poison", count=5))
    row = await lab.reclaim(ReclaimRequest(min_idle_ms=0))
    assert row.consumer == HEALTHY_CONSUMER
    assert len(row.claimed) == 2
    assert row.acked == 2
    assert await stream.pending(STREAM_KEY, GROUP, 20) == []
    assert "idle ≥ 0 ms" in row.detail


async def test_reclaim_with_nothing_stale_claims_nothing() -> None:
    lab, _ = _lab()
    row = await lab.reclaim(ReclaimRequest(min_idle_ms=0))
    assert row.claimed == [] and row.acked == 0
    assert "nothing was idle" in row.detail


async def test_panel_reports_log_length_and_pending_count() -> None:
    lab, _ = _lab()
    await lab.produce(ProduceRequest())
    panel = await lab.panel()
    assert panel.length == 1
    assert panel.last_id == panel.entries[-1].id
    assert panel.pending_count == 0
    await lab.consume(ConsumeRequest(mode="poison", count=5))
    assert (await lab.panel()).pending_count == 1


# ── The idempotent consumer ─────────────────────────────────────────────────


def _entry(event_id: str) -> StreamEntryRow:
    return StreamEntryRow(id=f"0-{event_id[-3:]}", event_id=event_id, event_type="t", payload="{}")


async def test_walk_processes_first_sightings_and_skips_repeats() -> None:
    consumer = IdempotentConsumer(FakeProcessedSet(), PROCESSED_SET_KEY)
    first = await consumer.walk([_entry("e-1"), _entry("e-2")])
    assert first.processed == ["e-1", "e-2"]
    assert first.skipped_duplicates == []
    second = await consumer.walk([_entry("e-2"), _entry("e-3")])
    assert second.processed == ["e-3"]
    assert second.skipped_duplicates == ["e-2"]  # the redelivery, absorbed


async def test_walk_on_an_empty_stream_processes_nothing() -> None:
    consumer = IdempotentConsumer(FakeProcessedSet(), PROCESSED_SET_KEY)
    walk = await consumer.walk([])
    assert walk.processed == [] and walk.skipped_duplicates == []


# ── The outbox relay ────────────────────────────────────────────────────────


async def test_relay_drains_unpublished_rows_and_marks_them() -> None:
    service, outbox, _, _ = _relay()
    await service.create_with_event(OutboxPostDraft(title="one"))
    first = await service.relay(RelayRequest())
    assert first.discovered == 1 and first.marked == 1 and not first.crashed
    assert outbox.rows[0].published_at is not None
    second = await service.relay(RelayRequest())
    assert second.discovered == 0  # drained: the next cycle finds nothing


async def test_crash_window_leaves_rows_unpublished_for_redelivery() -> None:
    service, outbox, stream, _ = _relay()
    await service.create_with_event(OutboxPostDraft(title="doomed to repeat"))
    crashed = await service.relay(RelayRequest(crash_before_mark=True))
    assert crashed.crashed and crashed.marked == 0 and len(crashed.published) == 1
    assert outbox.rows[0].published_at is None  # still in the work queue

    redelivered = await service.relay(RelayRequest())
    assert redelivered.discovered == 1 and redelivered.marked == 1
    event_ids = [row.event_id for row in stream.log]
    assert event_ids.count(event_ids[0]) == 2  # the SAME event id, twice on the stream


async def test_crash_request_with_nothing_to_publish_is_not_a_crash() -> None:
    service, _, _, _ = _relay()
    row = await service.relay(RelayRequest(crash_before_mark=True))
    assert not row.crashed and row.published == []


async def test_consume_reports_the_exactly_once_effect_after_a_crash() -> None:
    service, _, _, _ = _relay()
    await service.create_with_event(OutboxPostDraft(title="proof"))
    await service.relay(RelayRequest(crash_before_mark=True))
    await service.relay(RelayRequest())
    proof = await service.consume()
    assert proof.entries == 2  # two stream entries…
    assert proof.processed == 1  # …one event processed…
    assert proof.skipped_duplicates == 1  # …and one duplicate skipped
    assert "exactly-once EFFECT" in proof.proof


async def test_relay_cycles_are_single_flighted() -> None:
    service, _, stream, _ = _relay()
    await service.create_with_event(OutboxPostDraft(title="one event"))
    first, second = await _concurrent_relays(service)
    publishes = first.marked + second.marked
    assert publishes == 1  # the lock serialized the cycles; no double publish
    assert len(stream.log) == 1


async def _concurrent_relays(service: OutboxRelayService) -> tuple[RelayRow, RelayRow]:
    results = await asyncio.gather(
        service.relay(RelayRequest()), service.relay(RelayRequest())
    )
    return results[0], results[1]


async def test_outbox_stream_and_processed_set_keys_are_namespaced() -> None:
    assert OUTBOX_STREAM == "guide_demo:msg:outbox-events"
    assert PROCESSED_SET_KEY == "guide_demo:msg:processed"
