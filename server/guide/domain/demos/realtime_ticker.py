"""The realtime ticker demo payload: the panel + the live firehose stats.

Demo ``realtime:ticker`` (topic 28, INLINE in the SSE section): the panel
is the stream's front page — what ticks, at what (simulated) pace, how
reconnection resumes, and the endpoint to point an ``EventSource`` at —
while the stats endpoint is the firehose's odometer the client watches
move while it streams. All pure shaping over the ticker service; the
events themselves come from the LIVE stream, which is the demo's real
centerpiece.
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.realtime import frames as sse
from guide.domain.realtime.ticker import (
    DEFAULT_RETRY_MS,
    RING_CAPACITY,
    TICKER_SYMBOLS,
    TickerService,
)

STREAM_PATH: Final = "/api/realtime/ticker"
STATS_PATH: Final = "/api/demo/realtime/ticker/stats"
"""The live stream and this panel's stats endpoint — the tour names both."""


class EndpointRow(CamelModel):
    """One demo endpoint: the path and what trying it teaches."""

    path: str
    method: str
    teaches: str


class TickerPolicyRow(CamelModel):
    """The stream's fixed facts: pacing, symbols, resume, framing."""

    symbols: list[str]
    default_pace_ms: int
    retry_ms: int
    keepalive_every: int
    ring_capacity: int
    media_type: str


class TickerStatsRow(CamelModel):
    """The firehose counters, live from the service."""

    ticks_sent: int
    clients_served: int
    resume_replays: int
    ring_retained: int
    oldest_seq: int | None
    newest_seq: int | None


class TickerPanel(CamelModel):
    """Wire shape of ``GET /api/demo/realtime/ticker`` — the panel's contract."""

    policy: TickerPolicyRow
    stats: TickerStatsRow
    endpoints: list[EndpointRow]
    honesty_notes: list[str]
    reasoning: str


class TickerStatsPanel(CamelModel):
    """Wire shape of ``GET /api/demo/realtime/ticker/stats`` (the odometer)."""

    stats: TickerStatsRow


def _stats_row(service: TickerService) -> TickerStatsRow:
    stats = service.stats()
    return TickerStatsRow(
        ticks_sent=stats.ticks_sent,
        clients_served=stats.clients_served,
        resume_replays=stats.resume_replays,
        ring_retained=stats.ring_retained,
        oldest_seq=stats.oldest_seq,
        newest_seq=stats.newest_seq,
    )


def build_ticker_panel(service: TickerService) -> TickerPanel:
    """The panel: policy, live stats, the endpoint tour, the honesty notes."""
    return TickerPanel(
        policy=TickerPolicyRow(
            symbols=list(TICKER_SYMBOLS),
            default_pace_ms=750,
            retry_ms=DEFAULT_RETRY_MS,
            keepalive_every=4,
            ring_capacity=RING_CAPACITY,
            media_type=sse.SSE_MEDIA_TYPE,
        ),
        stats=_stats_row(service),
        endpoints=[
            EndpointRow(
                path=STREAM_PATH,
                method="GET",
                teaches="the live event stream (Last-Event-ID honored on reconnect)",
            ),
            EndpointRow(
                path=f"{STREAM_PATH}?limit=5",
                method="GET",
                teaches="a bounded stream — five live ticks, then an end event",
            ),
            EndpointRow(
                path=STATS_PATH,
                method="GET",
                teaches="the firehose odometer: ticks, clients, replays",
            ),
        ],
        honesty_notes=[
            "pacing is a simulated server-side sleep over a deterministic price walk",
            "replay is bounded by the ring — older Last-Event-Ids restart from now",
            "stats are process-local (one uvicorn worker), like the caching lab",
        ],
        reasoning=(
            "One shared market, one replayable ring: every connection mints into "
            "the same sequence, so any client's Last-Event-ID means something "
            "to the next."
        ),
    )


def build_ticker_stats(service: TickerService) -> TickerStatsPanel:
    """The odometer the streaming client polls."""
    return TickerStatsPanel(stats=_stats_row(service))
