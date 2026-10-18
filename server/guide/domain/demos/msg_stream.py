"""The stream-lab demo payloads: the state panel's roster, derived purely.

``GET /api/demo/msg/stream`` serves this payload — topic 22's first demo
(``msg:stream``), inline in the section that teaches logs vs queues. The
lab is INTERACTIVE: its buttons produce (XADD), consume as the healthy
or the poison consumer (XREADGROUP with or without XACK), list the
pending entries (XPENDING), and reclaim stale ones (XAUTOCLAIM). This
roster payload carries the panel's facts — the log in order, its length
and last id, the pending count — plus the copy that explains what each
button will do. The builder is PURE: every sentence derives from the
panel row and the service's own constants, so the payload can never
drift from what the stream really holds.
"""

from guide.core.serialization import CamelModel
from guide.domain.messaging.ports import (
    NAMESPACE_DISPLAY,
    PANEL_ENTRY_LIMIT,
    StreamEntryRow,
    StreamPanelRow,
)


class StreamPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/msg/stream`` — the state panel's roster."""

    namespace: str
    stream: str
    group: str
    healthy_consumer: str
    poison_consumer: str
    length: int
    displayed: int
    last_id: str | None
    entries: list[StreamEntryRow]
    pending_count: int
    produce_endpoint: str
    consume_endpoint: str
    pending_endpoint: str
    reclaim_endpoint: str
    reasoning: str


def build_stream_panel_payload(
    panel: StreamPanelRow,
    produce_endpoint: str,
    consume_endpoint: str,
    pending_endpoint: str,
    reclaim_endpoint: str,
) -> StreamPanelPayload:
    """Shape the roster (pure) — the reasoning derives from the panel row."""
    shown = panel.entries[-PANEL_ENTRY_LIMIT:]
    if panel.length:
        order_note = (
            f"The log holds {panel.length} entries, newest id {panel.last_id} — "
            f"ids are <milliseconds>-<sequence>, so the list below IS the arrival "
            f"order, and a replay of the stream would walk the same order again"
        )
    else:
        order_note = (
            "The stream is empty — the first produce will create it and its first "
            "entry id will carry the append's millisecond timestamp"
        )
    pending_note = (
        f"{panel.pending_count} delivered-but-unacknowledged entr"
        f"{'y waits' if panel.pending_count == 1 else 'ies wait'} in the group's "
        f"pending list — reclaim them once their idle time passes the threshold"
        if panel.pending_count
        else "nothing is pending — every delivery so far was acknowledged"
    )
    reasoning = (
        f"One Redis Stream ({panel.stream}) under {NAMESPACE_DISPLAY}, one consumer "
        f"group ({panel.group}), two consumer personas: {panel.healthy_consumer} "
        f"acks its work, {panel.poison_consumer} never does. {order_note}. "
        f"{pending_note}. Produce appends (XADD), consume reads new entries as a "
        f"persona (XREADGROUP, and XACK only for the healthy one), the pending list "
        f"shows who owns what (XPENDING), and reclaim moves stale entries back to "
        f"{panel.healthy_consumer} (XAUTOCLAIM) and finishes them."
    )
    return StreamPanelPayload(
        namespace=NAMESPACE_DISPLAY,
        stream=panel.stream,
        group=panel.group,
        healthy_consumer=panel.healthy_consumer,
        poison_consumer=panel.poison_consumer,
        length=panel.length,
        displayed=len(shown),
        last_id=panel.last_id,
        entries=shown,
        pending_count=panel.pending_count,
        produce_endpoint=produce_endpoint,
        consume_endpoint=consume_endpoint,
        pending_endpoint=pending_endpoint,
        reclaim_endpoint=reclaim_endpoint,
        reasoning=reasoning,
    )
