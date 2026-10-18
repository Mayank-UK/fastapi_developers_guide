"""The idempotent consumer: dedupe by event id over a processed-set.

At-least-once delivery means every consumer WILL see some events twice —
redelivery after a crash, a rebalance, a duplicate publish. The
exactly-once EXPERIENCE is built on the consuming side, and this module
is its whole shape: check the processed-set BEFORE doing the work,
remember the event id AFTER the work completes. The order is the
guarantee, and it is a trade:

- remember BEFORE the work and a crash mid-work loses the event forever
  (at-most-once — the unsafe side of the trade);
- remember AFTER the work and a crash between work and remember replays
  the work on redelivery (at-most-once work gap closed by making the
  work itself idempotent, or accepting the small duplicate window).

This engine takes the second side — duplicates are auditable, losses
are not — and exists so the trade is a typed, testable artifact rather
than folklore. The walk is ordered awaits over the ``ProcessedEventStore``
port: no sleeps, no locks, and the counts are pinned by the order of the
awaits, so a fake store reproduces every guarantee deterministically.
"""

from typing import Final

import structlog

from guide.domain.messaging.ports import (
    DedupeWalk,
    ProcessedEventStore,
    StreamEntryRow,
)

logger = structlog.get_logger()

REMEMBER_ORDER_NOTE: Final = (
    "the processed-set is checked before the work and remembered after it — "
    "crashes may replay work, never lose it"
)
"""The one-sentence form of the ordering decision; the topic quotes it."""


class IdempotentConsumer:
    """Walk entries, processing each event id at most once."""

    def __init__(self, store: ProcessedEventStore, set_key: str) -> None:
        self._store = store
        self._set_key = set_key

    async def walk(self, entries: list[StreamEntryRow]) -> DedupeWalk:
        """Process every entry in order; first sightings work, repeats skip.

        The work itself lives with the caller — for this guide's demo the
        accounting IS the work (a real consumer would run its handler
        between the seen check and the remember). Duplicates answer with
        a skip, the event's stable id already in the set.
        """
        processed: list[str] = []
        skipped_duplicates: list[str] = []
        for entry in entries:
            if await self._store.seen(self._set_key, entry.event_id):
                skipped_duplicates.append(entry.event_id)
                continue
            await self._store.remember(self._set_key, entry.event_id)
            processed.append(entry.event_id)
        if skipped_duplicates:
            logger.info(
                "idempotent_consumer_walked",
                set_key=self._set_key,
                processed=len(processed),
                duplicates=len(skipped_duplicates),
            )
        return DedupeWalk(processed=processed, skipped_duplicates=skipped_duplicates)
