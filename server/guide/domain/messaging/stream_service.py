"""The stream lab engine: produce → group-read → ack, pending, reclaim.

``StreamLabService`` is the msg:stream demo's teaching artifact — the
consumer-group lifecycle as real orchestration over the ``StreamProducer``
and ``StreamConsumer`` ports. The healthy consumer reads new entries and
acknowledges them (the happy path: delivery leaves the pending entries
list the moment work completes); the POISON consumer is the failure
study — it reads and never acks, so every delivery lands in the group's
pending entries list (PEL) and sits there, idle time growing, until
``reclaim`` moves the stale ones back to the healthy consumer with
XAUTOCLAIM and finishes the work on their behalf.

Everything here is ordered awaits and zero sleeps: the lab's guarantees
(read-then-ack bookkeeping, pending visibility, reclaim bounds) are
pinned by the awaits' ORDER, so fakes at the port boundary reproduce
them deterministically in tests. The group is ensured (idempotently) at
the top of every round — created at ``0-0``, so a group created after
appends still sees the whole log, which is itself the replay lesson.
"""

import json
from typing import Final

import structlog

from guide.domain.db.ids import Uuid7Mint
from guide.domain.messaging.ports import (
    EVENT_NOTE_TYPE,
    NAMESPACE,
    PENDING_LIMIT,
    RECLAIM_COUNT,
    ConsumeRequest,
    ConsumeRow,
    EventDraft,
    PendingListRow,
    ProduceRequest,
    ProduceRow,
    ReclaimRequest,
    ReclaimRow,
    StreamConsumer,
    StreamPanelRow,
    StreamProducer,
)

logger = structlog.get_logger()

STREAM_KEY: Final = f"{NAMESPACE}stream"
"""The lab's Redis Stream — an append-only log under the demo namespace."""

GROUP: Final = f"{NAMESPACE}workers"
"""The lab's one consumer group — delivery state lives per group."""

HEALTHY_CONSUMER: Final = "healthy-worker"
"""The consumer that acknowledges: the path every real worker should take."""

POISON_CONSUMER: Final = "poison-worker"
"""The consumer that reads without acking — a stuck (or crashing) worker."""


class StreamLabService:
    """Produce, consume (healthy or poison), inspect pending, reclaim."""

    def __init__(self, producer: StreamProducer, consumer: StreamConsumer) -> None:
        self._producer = producer
        self._consumer = consumer
        self._mint = Uuid7Mint()

    async def produce(self, request: ProduceRequest) -> ProduceRow:
        """Mint a UUIDv7 event id and append the note — XADD, one entry."""
        event_id = self._mint.mint()
        payload = json.dumps({"note": request.note}, sort_keys=True)
        entry_id = await self._producer.append(
            STREAM_KEY,
            EventDraft(
                event_id=str(event_id),
                event_type=EVENT_NOTE_TYPE,
                payload=payload,
            ),
        )
        entries = await self._consumer.entries(STREAM_KEY)
        detail = (
            f"XADD appended event {event_id} as entry {entry_id} — the stream is now "
            f"{len(entries)} entries long and the entry id's millisecond prefix is the "
            f"order it landed in"
        )
        logger.info("stream_produced", stream=STREAM_KEY, entry_id=entry_id)
        return ProduceRow(
            stream=STREAM_KEY,
            event_id=str(event_id),
            entry_id=entry_id,
            note=request.note,
            length=len(entries),
            detail=detail,
        )

    async def consume(self, request: ConsumeRequest) -> ConsumeRow:
        """One read round as the chosen consumer persona.

        The healthy consumer acks what it is delivered — acknowledgement
        is the WORK-DONE signal, and until it happens the entries belong
        to this consumer in the group's PEL. The poison consumer skips
        the ack on purpose: its deliveries pile up pending, which is
        exactly what a crashed or stuck worker looks like from outside.
        """
        await self.ensure_ready()
        consumer = HEALTHY_CONSUMER if request.mode == "healthy" else POISON_CONSUMER
        delivered = await self._consumer.read_new(STREAM_KEY, GROUP, consumer, request.count)
        acked = 0
        if request.mode == "healthy" and delivered:
            acked = await self._consumer.ack(STREAM_KEY, GROUP, [row.id for row in delivered])
            detail = (
                f"{consumer} read {len(delivered)} new entr"
                f"{'y' if len(delivered) == 1 else 'ies'} and acknowledged {acked} — "
                f"work done, the entries left the pending list for good"
            )
        elif delivered:
            detail = (
                f"{POISON_CONSUMER} read {len(delivered)} new entr"
                f"{'y' if len(delivered) == 1 else 'ies'} and NEVER ACKED — they sit in "
                f"the group's pending entries list, owned by a consumer that will not "
                f"finish; reclaim them with XAUTOCLAIM once their idle time grows"
            )
        else:
            detail = (
                f"{consumer} read nothing — no undelivered entries remain for this "
                f"group (produce more, or check the pending list for entries already "
                f"owned by a consumer)"
            )
        logger.info(
            "stream_consumed",
            stream=STREAM_KEY,
            consumer=consumer,
            delivered=len(delivered),
            acked=acked,
        )
        return ConsumeRow(
            stream=STREAM_KEY,
            group=GROUP,
            consumer=consumer,
            mode=request.mode,
            delivered=delivered,
            acked=acked,
            detail=detail,
        )

    async def pending(self) -> PendingListRow:
        """The group's pending entries list — who owns what, for how long."""
        await self.ensure_ready()
        rows = await self._consumer.pending(STREAM_KEY, GROUP, PENDING_LIMIT)
        if rows:
            owners = sorted({row.consumer for row in rows})
            detail = (
                f"{len(rows)} pending entr{'y is' if len(rows) == 1 else 'ies are'} "
                f"delivered-but-unacknowledged, owned by {', '.join(owners)} — idle "
                f"milliseconds and delivery counts straight from XPENDING"
            )
        else:
            detail = (
                "the pending entries list is empty — every delivery so far was "
                "acknowledged (or nothing has been delivered yet)"
            )
        return PendingListRow(stream=STREAM_KEY, group=GROUP, entries=rows, detail=detail)

    async def reclaim(self, request: ReclaimRequest) -> ReclaimRow:
        """XAUTOCLAIM stale pending entries to the healthy consumer, then ack.

        ``min_idle_ms`` is the visibility timeout: entries whose idle time
        is below it are presumed still being worked on and left alone;
        entries past it are presumed abandoned (their consumer crashed,
        hung, or is the poison persona) and change ownership to
        ``healthy-worker``, which finishes the work — the ack — for them.
        """
        await self.ensure_ready()
        claimed = await self._consumer.claim(
            STREAM_KEY, GROUP, HEALTHY_CONSUMER, request.min_idle_ms, RECLAIM_COUNT
        )
        acked = 0
        if claimed:
            acked = await self._consumer.ack(STREAM_KEY, GROUP, [row.id for row in claimed])
            detail = (
                f"XAUTOCLAIM moved {len(claimed)} entr"
                f"{'y' if len(claimed) == 1 else 'ies'} idle ≥ {request.min_idle_ms} ms "
                f"to {HEALTHY_CONSUMER}, which finished the work (acked {acked}) — the "
                f"abandoned deliveries are complete and out of the pending list"
            )
        else:
            detail = (
                f"nothing was idle ≥ {request.min_idle_ms} ms — the pending list is "
                f"either empty or its entries are still inside their visibility "
                f"timeout; lower the threshold or wait for the idle time to grow"
            )
        logger.info(
            "stream_reclaimed",
            stream=STREAM_KEY,
            min_idle_ms=request.min_idle_ms,
            claimed=len(claimed),
        )
        return ReclaimRow(
            stream=STREAM_KEY,
            group=GROUP,
            consumer=HEALTHY_CONSUMER,
            min_idle_ms=request.min_idle_ms,
            claimed=claimed,
            acked=acked,
            detail=detail,
        )

    async def panel(self) -> StreamPanelRow:
        """The state panel's facts: the log in order, plus the backlog."""
        await self.ensure_ready()
        entries = await self._consumer.entries(STREAM_KEY)
        pending_rows = await self._consumer.pending(STREAM_KEY, GROUP, PENDING_LIMIT)
        return StreamPanelRow(
            stream=STREAM_KEY,
            group=GROUP,
            healthy_consumer=HEALTHY_CONSUMER,
            poison_consumer=POISON_CONSUMER,
            length=len(entries),
            last_id=entries[-1].id if entries else None,
            entries=entries,
            pending_count=len(pending_rows),
        )

    async def ensure_ready(self) -> None:
        """Create the group if needed (idempotent) — every round starts here."""
        await self._consumer.ensure_group(STREAM_KEY, GROUP)
