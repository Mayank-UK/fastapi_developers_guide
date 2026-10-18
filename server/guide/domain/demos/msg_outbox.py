"""The outbox demo payloads: the state panel's roster, derived purely.

``GET /api/demo/msg/outbox`` serves this payload — topic 22's second
demo (``msg:outbox``), inline in the section that teaches the
transactional outbox. The lab is INTERACTIVE: its buttons create a
post-with-event (ONE PostgreSQL transaction — the response shows both
rows), run a relay cycle (publish to the Redis Stream and mark, or
"die" before marking to open the at-least-once window), and walk the
stream through the idempotent consumer (dedupe by event id — the
exactly-once EFFECT's counts). The builder is PURE: every sentence
derives from the panel row, so the payload can never drift from what
the table and the stream really hold.
"""

from guide.core.serialization import CamelModel
from guide.domain.messaging.ports import (
    NAMESPACE_DISPLAY,
    OutboxPanelRow,
    OutboxRow,
    OutboxStatsRow,
    OutboxTelemetryRow,
    StreamEntryRow,
)


class OutboxPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/msg/outbox`` — the state panel's roster."""

    namespace: str
    stream: str
    table: str
    stats: OutboxStatsRow
    outbox: list[OutboxRow]
    stream_entries: list[StreamEntryRow]
    telemetry: OutboxTelemetryRow
    posts_endpoint: str
    relay_endpoint: str
    consume_endpoint: str
    reasoning: str


def build_outbox_panel_payload(
    panel: OutboxPanelRow,
    posts_endpoint: str,
    relay_endpoint: str,
    consume_endpoint: str,
) -> OutboxPanelPayload:
    """Shape the roster (pure) — the reasoning derives from the panel row."""
    stats = panel.stats
    telemetry = panel.telemetry
    if stats.total:
        backlog_note = (
            f"The {panel.table} table holds {stats.total} event(s): {stats.published} "
            f"published, {stats.unpublished} still waiting — the relay's work queue "
            f"is a partial index over exactly those waiting rows"
        )
    else:
        backlog_note = (
            f"The {panel.table} table is empty — create a post-with-event and the "
            f"same transaction writes the post AND its event, both or neither"
        )
    if telemetry.crash_simulations:
        crash_note = (
            f"{telemetry.crash_simulations} crash simulation(s) so far left delivered-"
            f"but-unmarked rows behind; the next cycle published them again and the "
            f"idempotent consumer skipped {telemetry.duplicates_skipped} duplicate(s) "
            f"in total — that is the exactly-once EFFECT, not a broker promise"
        )
    else:
        crash_note = (
            "run the relay with the crash window open to watch at-least-once "
            "delivery appear: the stream gains a duplicate the consumer then skips"
        )
    reasoning = (
        f"One PostgreSQL table ({panel.table}) and one Redis Stream ({panel.stream}) "
        f"under {NAMESPACE_DISPLAY}, bridged by a relay. {backlog_note}. The create "
        f"button commits a post and its event in ONE transaction; the relay button "
        f"polls unpublished rows, publishes each to the stream, and marks them — "
        f"unless you send it to die in the window between publish and mark. "
        f"{crash_note}."
    )
    return OutboxPanelPayload(
        namespace=NAMESPACE_DISPLAY,
        stream=panel.stream,
        table=panel.table,
        stats=stats,
        outbox=panel.outbox,
        stream_entries=panel.stream_entries,
        telemetry=telemetry,
        posts_endpoint=posts_endpoint,
        relay_endpoint=relay_endpoint,
        consume_endpoint=consume_endpoint,
        reasoning=reasoning,
    )
