"""The simulated market: deterministic prices, one shared log, paced streams.

Every connection to the ticker watches the SAME market: ``next_event``
mints the globally next event under a lock (two concurrent clients never
see the same seq), appends it to the shared bounded ring, and returns it
— so the Last-Event-ID of one connection is meaningful to the next. The
prices are a DETERMINISTIC function of (symbol, seq): smooth waves plus a
hashed flutter step, the same values on every boot and every replay,
with the simulation labeled everywhere it is shown. Pacing is equally
honest: ``stream_ticker_frames`` waits ``pace_seconds`` between ticks via
an injected ``sleeper`` (``asyncio.sleep`` in production, an instant fake
in tests) — a stand-in for the rate a real feed's provider would set.

The stream's wire behavior, in order: a ``ready`` event carrying the
reconnect hint (``retry``) and what the server replayed; the replayed
events themselves (each with its ``id``); then paced live ``tick`` events
until the client disconnects or the optional ``limit`` is reached, with
``keepalive`` comments interleaved on a counter so the mechanism is
observable, and an ``end`` event when a limit stops the stream.
"""

import asyncio
import hashlib
import json
import math
import time
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.realtime.frames import encode_keepalive, encode_sse_event
from guide.domain.realtime.log import BoundedEventLog

Clock = Callable[[], float]
"""Epoch-seconds clock, injected for deterministic tests."""

Sleeper = Callable[[float], Awaitable[None]]
"""One paced wait, injected for tests (production: ``asyncio.sleep``)."""

TICKER_EVENT: Final = "tick"
READY_EVENT: Final = "ready"
END_EVENT: Final = "end"

TICKER_SYMBOLS: Final[tuple[str, ...]] = ("FDG", "ASY", "PYC")
"""The traded names — rotation assigns one symbol per minted seq."""

_BASE_PRICES: Final[dict[str, float]] = {"FDG": 128.0, "ASY": 42.25, "PYC": 64.5}

RING_CAPACITY: Final[int] = 120
"""Replay window: how many events the ring retains (the resume ceiling)."""

DEFAULT_RETRY_MS: Final[int] = 3000
"""The ``retry`` hint: how long a reconnecting EventSource should wait."""


class TickerEvent(CamelModel):
    """One minted tick; the SSE ``data`` payload as well as the logged event."""

    seq: int
    symbol: str
    price: float
    change: float
    at: float


@dataclass(frozen=True, slots=True)
class TickerStats:
    """The firehose counters the demo panel serves."""

    ticks_sent: int
    clients_served: int
    resume_replays: int
    ring_capacity: int
    ring_retained: int
    oldest_seq: int | None
    newest_seq: int | None


def _phase(symbol: str) -> float:
    """A stable per-symbol phase offset, so each name waves differently."""
    return (zlib.crc32(symbol.encode("ascii")) % 997) / 997 * math.tau


def _flutter_bit(symbol: str, seq: int) -> int:
    """A deterministic up/down bit — hashed, never ``random`` (replayability)."""
    digest = hashlib.sha256(f"{symbol}:{seq}".encode("ascii")).digest()
    return digest[0] & 1


def _price_at(symbol: str, seq: int) -> float:
    """The price of ``symbol`` at ``seq`` — pure, so replays are exact."""
    base = _BASE_PRICES[symbol]
    phase = _phase(symbol)
    wave = 0.05 * math.sin(seq / 9.0 + phase)
    flutter = 0.008 * math.sin(seq * 2.399 + phase * 1.7)
    step = 1.0 if _flutter_bit(symbol, seq) else -1.0
    return round(base * (1.0 + wave + flutter + step * 0.004), 2)


def _mint_event(seq: int, at: float) -> TickerEvent:
    """Build the event for a seq: rotating symbol, price, change vs last round."""
    symbol = TICKER_SYMBOLS[(seq - 1) % len(TICKER_SYMBOLS)]
    price = _price_at(symbol, seq)
    if seq > len(TICKER_SYMBOLS):
        previous = _price_at(symbol, seq - len(TICKER_SYMBOLS))
    else:  # the first round of each symbol compares against its base price
        previous = _BASE_PRICES[symbol]
    change = round(price - previous, 2)
    return TickerEvent(seq=seq, symbol=symbol, price=price, change=change, at=at)


def _frame_event(event: TickerEvent) -> str:
    """One dispatchable SSE frame: the seq as the id, the event as the data."""
    return encode_sse_event(event.model_dump_json(), event=TICKER_EVENT, id=str(event.seq))


class TickerService:
    """The shared market: minting, the replay ring, and the live counters."""

    def __init__(self, *, clock: Clock | None = None, ring_capacity: int = RING_CAPACITY) -> None:
        """One service per app; the clock injects determinism for tests."""
        self._clock: Clock = clock or time.time
        self._log = BoundedEventLog[TickerEvent](ring_capacity)
        self._next_seq = 0
        self._mint_lock = asyncio.Lock()
        self._ticks_sent = 0
        self._clients_served = 0
        self._resume_replays = 0

    @property
    def log(self) -> BoundedEventLog[TickerEvent]:
        """The shared ring — read for replay, written only by ``next_event``."""
        return self._log

    def stats(self) -> TickerStats:
        """The firehose counters (process-local by design, like the caching lab)."""
        return TickerStats(
            ticks_sent=self._ticks_sent,
            clients_served=self._clients_served,
            resume_replays=self._resume_replays,
            ring_capacity=self._log.capacity,
            ring_retained=len(self._log),
            oldest_seq=self._log.oldest_seq,
            newest_seq=self._log.newest_seq,
        )

    def open_client(self) -> None:
        """Count one stream opening (every connection, fresh or resumed)."""
        self._clients_served += 1

    def replay_after(self, last_seq: int) -> list[TickerEvent]:
        """The replay for a reconnect: contiguous run, or [] for a fresh start.

        A NON-empty replay is the thing worth counting — it means a client
        genuinely resumed rather than restarted.
        """
        events = self._log.events_after(last_seq)
        if events:
            self._resume_replays += 1
        return events

    async def next_event(self) -> TickerEvent:
        """Mint the globally next event into the shared ring (serialized)."""
        async with self._mint_lock:
            self._next_seq += 1
            event = _mint_event(self._next_seq, self._clock())
            self._log.append(event.seq, event)
            self._ticks_sent += 1
            return event


async def _never_disconnected() -> bool:
    """The default disconnect probe: tests without a Request stay connected."""
    return False


async def stream_ticker_frames(
    service: TickerService,
    *,
    last_event_id: int | None,
    limit: int,
    pace_seconds: float,
    keepalive_every: int,
    retry_ms: int = DEFAULT_RETRY_MS,
    sleeper: Sleeper = asyncio.sleep,
    is_disconnected: Callable[[], Awaitable[bool]] = _never_disconnected,
) -> AsyncIterator[str]:
    """The SSE body: ready frame, replayed events, then paced live ticks.

    ``limit`` bounds the LIVE ticks (0 = stream until the client goes away)
    so tests and the terminal tour get finite streams; ``keepalive_every``
    emits a comment frame every N-th wait (0 disables) purely to make the
    mechanism observable on the wire. Disconnects are detected both ways:
    the probe is polled each iteration, and a client that vanishes cancels
    the generator between yields — the loop holds nothing to clean up.
    """
    service.open_client()
    replay = service.replay_after(last_event_id) if last_event_id is not None else []
    yield encode_sse_event(
        json.dumps(
            {
                "replayed": len(replay),
                "resumeWindow": service.log.capacity,
                "symbols": list(TICKER_SYMBOLS),
                "paceMs": round(pace_seconds * 1000),
                "simulated": True,
            }
        ),
        event=READY_EVENT,
        retry_ms=retry_ms,
    )
    for event in replay:
        yield _frame_event(event)

    live_ticks = 0
    while limit == 0 or live_ticks < limit:
        if keepalive_every and live_ticks and live_ticks % keepalive_every == 0:
            yield encode_keepalive()
        await sleeper(pace_seconds)
        if await is_disconnected():
            return  # the client is gone: stop without an end frame
        event = await service.next_event()
        live_ticks += 1
        yield _frame_event(event)

    if limit:
        yield encode_sse_event(
            json.dumps({"reason": "limit", "liveTicks": live_ticks}),
            event=END_EVENT,
        )
