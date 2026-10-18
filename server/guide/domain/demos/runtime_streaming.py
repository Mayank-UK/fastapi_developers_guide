"""Streaming demo payload: a real async generator, served as NDJSON lines.

``GET /api/demo/runtime/streaming`` serves this stream. The generator is
the teaching object: ``stream_runtime_chunks`` is an ``async def`` that
``yield``s, so each ``__anext__()`` runs the body only as far as the next
``yield`` — and because the body ``await``s a tiny tick between items, the
producer's pace and the consumer's pace genuinely interleave on the event
loop. The sequence is bounded and fixed (a deterministic open/item/closed
shape: count and order never vary); the closing line carries the measured
wall-clock cost of the whole stream. The router wraps the generator in a
``StreamingResponse`` with the ``application/x-ndjson`` media type — one
JSON object per line, the wire shape log tails and event feeds use.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Final, Literal

from guide.core.serialization import CamelModel

STREAM_ITEMS: Final[int] = 6
"""Items between the open and closed lines — fixed, so the count is testable."""

STREAM_TICK: Final[float] = 0.002
"""Seconds of simulated I/O between items (2 ms: a real await, a tiny cost)."""


class StreamChunk(CamelModel):
    """One NDJSON line of the stream; wire keys are camelCase."""

    seq: int
    kind: Literal["open", "item", "closed"]
    label: str
    detail: str | None = None
    items_delivered: int | None = None
    total_ms: float | None = None


def _encode(chunk: StreamChunk) -> str:
    """One wire line: camelCase JSON, optional-absent fields omitted."""
    return chunk.model_dump_json(by_alias=True, exclude_none=True) + "\n"


async def stream_runtime_chunks(
    item_count: int = STREAM_ITEMS, tick: float = STREAM_TICK
) -> AsyncIterator[str]:
    """The demo's async generator: open line, awaited items, closing line."""
    started = time.perf_counter()
    yield _encode(
        StreamChunk(
            seq=0,
            kind="open",
            label="runtime-stream",
            detail=f"{item_count} items follow, one per awaited tick",
        )
    )
    for index in range(1, item_count + 1):
        await asyncio.sleep(tick)  # the simulated I/O between yields
        yield _encode(
            StreamChunk(
                seq=index,
                kind="item",
                label=f"loop-tick-{index}",
                detail=f"yielded after {tick * 1000:.0f}ms of simulated io",
            )
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    yield _encode(
        StreamChunk(
            seq=item_count + 1,
            kind="closed",
            label="stream-complete",
            items_delivered=item_count,
            total_ms=round(elapsed_ms, 2),
        )
    )
