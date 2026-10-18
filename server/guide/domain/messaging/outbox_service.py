"""The transactional-outbox relay: poll unpublished → publish → mark.

``OutboxRelayService`` is the msg:outbox demo's engine, and every moving
part of the pattern lives here as real orchestration over three ports:
``OutboxAccess`` (the outbox table in PostgreSQL, including the
one-transaction business write), ``StreamProducer`` (XADD to the demo's
Redis Stream), and ``ProcessedEventStore`` (the idempotent consumer's
processed-set, driven through ``IdempotentConsumer``).

The relay cycle is deliberately three separated steps — poll, publish
each, mark all — because the GAPS between them are the teaching: publish
and mark cannot be atomic across two stores, so a relay that dies in the
gap leaves rows that are delivered-but-unmarked, and the next cycle
publishes them AGAIN. That is not a bug to fix; it is at-least-once
delivery made visible, and the idempotent consumer on the other side is
what turns it into an exactly-once EFFECT. ``crash_before_mark`` is the
simulated death in that exact window (honest label, real bookkeeping).

A per-service ``asyncio.Lock`` single-flights the cycle: two concurrent
relay rounds must not discover the same unpublished rows and double-
publish beyond what the crash window already teaches. Counters are
process-local and mutated only between awaits on the serving loop.
"""

import asyncio
from typing import Final

import structlog

from guide.domain.messaging.idempotence import IdempotentConsumer
from guide.domain.messaging.ports import (
    NAMESPACE,
    PANEL_ENTRY_LIMIT,
    EventDraft,
    OutboxAccess,
    OutboxConsumeRow,
    OutboxPanelRow,
    OutboxPostDraft,
    OutboxTelemetryRow,
    OutboxWriteRow,
    ProcessedEventStore,
    PublishedEntryRow,
    RelayRequest,
    RelayRow,
    StreamConsumer,
    StreamProducer,
)

logger = structlog.get_logger()

OUTBOX_STREAM: Final = f"{NAMESPACE}outbox-events"
"""The stream the relay publishes to — the outbox's delivery side."""

PROCESSED_SET_KEY: Final = f"{NAMESPACE}processed"
"""The idempotent consumer's processed-set — event ids already handled."""

OUTBOX_TABLE: Final = "outbox"
"""The outbox table's name, as the panel displays it."""

PANEL_ROW_LIMIT: Final = 10
"""How many outbox rows the panel's table view carries."""


class OutboxRelayService:
    """Create-with-event, relay (with the crash window), consume idempotently."""

    def __init__(
        self,
        outbox: OutboxAccess,
        producer: StreamProducer,
        consumer: StreamConsumer,
        processed: ProcessedEventStore,
    ) -> None:
        self._outbox = outbox
        self._producer = producer
        self._consumer = consumer
        self._walk = IdempotentConsumer(processed, PROCESSED_SET_KEY)
        self._relay_lock = asyncio.Lock()
        self._cycle = 0
        self._creates = 0
        self._crashes = 0
        self._publishes = 0
        self._events_processed = 0
        self._duplicates_skipped = 0

    async def create_with_event(self, draft: OutboxPostDraft) -> OutboxWriteRow:
        """The dual write, atomic: post and event commit together or not at all."""
        row = await self._outbox.create_post_with_event(draft)
        if row.committed:
            self._creates += 1
            logger.info(
                "outbox_written",
                event_id=row.event.event_id if row.event else None,
                aggregate=row.event.aggregate if row.event else None,
            )
        return row

    async def relay(self, request: RelayRequest) -> RelayRow:
        """One relay cycle: poll unpublished → publish each → mark (or die first).

        Single-flighted: the lock serializes concurrent cycles, so a
        second caller finds the rows already marked rather than racing
        the first caller's publish loop.
        """
        async with self._relay_lock:
            self._cycle += 1
            discovered = await self._outbox.unpublished(request.batch)
            published: list[PublishedEntryRow] = []
            for row in discovered:
                entry_id = await self._producer.append(
                    OUTBOX_STREAM,
                    EventDraft(
                        event_id=row.event_id,
                        event_type=row.event_type,
                        payload=row.payload,
                    ),
                )
                published.append(
                    PublishedEntryRow(
                        event_id=row.event_id, entry_id=entry_id, aggregate=row.aggregate
                    )
                )
                self._publishes += 1
            crashed = request.crash_before_mark and bool(published)
            if crashed:
                self._crashes += 1
                detail = (
                    f"cycle {self._cycle} published {len(published)} event(s) then DIED "
                    f"before marking — the rows are still unpublished, so the next "
                    f"cycle will publish them again: at-least-once, on purpose"
                )
                logger.info("outbox_relay_crashed", cycle=self._cycle, published=len(published))
                return RelayRow(
                    cycle=self._cycle,
                    stream=OUTBOX_STREAM,
                    discovered=len(discovered),
                    published=published,
                    marked=0,
                    crashed=True,
                    detail=detail,
                )
            marked = (
                await self._outbox.mark_published([row.event_id for row in published])
                if published
                else 0
            )
            if published:
                detail = (
                    f"cycle {self._cycle} polled {len(discovered)} unpublished row(s), "
                    f"published each to {OUTBOX_STREAM}, and stamped published_at on "
                    f"{marked} — the rows are done and the next cycle finds nothing"
                )
            else:
                detail = (
                    f"cycle {self._cycle} found nothing unpublished — the outbox is "
                    f"drained; create a post-with-event to feed the next cycle"
                )
            logger.info(
                "outbox_relayed", cycle=self._cycle, published=len(published), marked=marked
            )
            return RelayRow(
                cycle=self._cycle,
                stream=OUTBOX_STREAM,
                discovered=len(discovered),
                published=published,
                marked=marked,
                crashed=False,
                detail=detail,
            )

    async def consume(self) -> OutboxConsumeRow:
        """Walk the outbox stream through the idempotent consumer's counts.

        Reads the WHOLE log (XRANGE — replay is the log's promise) and
        dedupes by event id: entries whose id is in the processed-set are
        skipped as duplicates, everything else counts as processed. After
        a crash-window redelivery these two numbers ARE the proof: more
        entries on the stream than events processed, difference skipped.
        """
        entries = await self._consumer.entries(OUTBOX_STREAM)
        walk = await self._walk.walk(entries)
        self._events_processed += len(walk.processed)
        self._duplicates_skipped += len(walk.skipped_duplicates)
        proof = (
            f"{len(entries)} stream entries → {len(walk.processed)} processed, "
            f"{len(walk.skipped_duplicates)} duplicate(s) skipped — the processed-set "
            f"made redelivery harmless, which is the exactly-once EFFECT"
        )
        return OutboxConsumeRow(
            stream=OUTBOX_STREAM,
            entries=len(entries),
            processed=len(walk.processed),
            skipped_duplicates=len(walk.skipped_duplicates),
            proof=proof,
        )

    async def panel(self) -> OutboxPanelRow:
        """The state panel's facts: table counts, recent rows, stream, counters."""
        stats = await self._outbox.stats()
        recent = await self._outbox.recent(PANEL_ROW_LIMIT)
        stream_entries = await self._consumer.entries(OUTBOX_STREAM)
        return OutboxPanelRow(
            stream=OUTBOX_STREAM,
            table=OUTBOX_TABLE,
            stats=stats,
            outbox=recent,
            stream_entries=stream_entries[-PANEL_ENTRY_LIMIT:],
            telemetry=self._telemetry(),
        )

    def _telemetry(self) -> OutboxTelemetryRow:
        return OutboxTelemetryRow(
            creates=self._creates,
            relay_cycles=self._cycle,
            crash_simulations=self._crashes,
            publishes=self._publishes,
            events_processed=self._events_processed,
            duplicates_skipped=self._duplicates_skipped,
        )
