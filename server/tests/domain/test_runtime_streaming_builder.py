"""Builder unit tests: the streaming demo's async generator, driven directly.

Count and order are deterministic by design (open → six items → closed);
only the closing line's totalMs is measured. Consuming the generator here
exercises the real async-iteration protocol — each yield awaited in turn.
"""

import json

from guide.domain.demos.runtime_streaming import (
    STREAM_ITEMS,
    STREAM_TICK,
    stream_runtime_chunks,
)


async def _collect() -> list[dict[str, object]]:
    """Consume the generator through the async-iteration protocol."""
    chunks = [
        json.loads(line) async for line in stream_runtime_chunks()
    ]
    return chunks


async def test_stream_shape_is_open_items_closed() -> None:
    chunks = await _collect()
    kinds = [chunk["kind"] for chunk in chunks]
    assert kinds == ["open", *["item"] * STREAM_ITEMS, "closed"]
    assert len(chunks) == STREAM_ITEMS + 2


async def test_sequence_numbers_are_dense_and_ordered() -> None:
    chunks = await _collect()
    assert [chunk["seq"] for chunk in chunks] == list(range(STREAM_ITEMS + 2))


async def test_labels_are_deterministic() -> None:
    chunks = await _collect()
    assert chunks[0]["label"] == "runtime-stream"
    assert [chunk["label"] for chunk in chunks[1:-1]] == [
        f"loop-tick-{index}" for index in range(1, STREAM_ITEMS + 1)
    ]
    assert chunks[-1]["label"] == "stream-complete"


async def test_closing_line_reports_the_count_and_a_measured_total() -> None:
    chunks = await _collect()
    closed = chunks[-1]
    assert closed["itemsDelivered"] == STREAM_ITEMS
    # Measured wall-clock of the whole stream: ≥ the sum of awaited ticks.
    assert isinstance(closed["totalMs"], float)
    assert closed["totalMs"] >= STREAM_ITEMS * STREAM_TICK * 1000 - 0.1


async def test_every_line_is_camelcase_json_with_newline_framing() -> None:
    lines = [line async for line in stream_runtime_chunks()]
    assert all(line.endswith("\n") for line in lines)
    parsed = [json.loads(line) for line in lines]
    assert {"seq", "kind", "label"} <= set(parsed[0])
    assert "itemsDelivered" in parsed[-1]
    # Family wire convention: optional-absent fields are OMITTED, not null.
    assert "itemsDelivered" not in parsed[0]
    assert "totalMs" not in parsed[1]
