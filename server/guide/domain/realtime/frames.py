"""Server-sent events framing: the ``text/event-stream`` wire format, pure.

The format (the WHATWG HTML standard's event-stream grammar — the part
every ``EventSource`` implements): an event is a block of ``field: value``
lines — ``event``, ``data``, ``id``, ``retry`` — terminated by ONE blank
line, and that blank line is what makes a client DISPATCH the event. Data
may span multiple lines (each carries its own ``data:`` prefix; the client
joins them with newlines into one payload). A line starting with a colon
is a COMMENT: clients ignore it entirely, which is exactly why a periodic
comment keeps intermediaries from closing an otherwise idle connection —
the keepalive trick. Everything here is pure string shaping, so the unit
tests pin the bytes themselves.
"""

from typing import Final

CRLF: Final = "\r\n"
"""Line endings some clients send; frames are always emitted with LF."""

FIELD_EVENT: Final = "event"
FIELD_ID: Final = "id"
FIELD_RETRY: Final = "retry"

SSE_MEDIA_TYPE: Final = "text/event-stream"
"""The media type that turns a streaming response into an event stream."""


def _single_line_value(value: str) -> str:
    """One field value: CRLF normalized away, a single leading space dropped.

    The grammar allows ``field: value`` with exactly one optional space
    after the colon — stripping one leading space here keeps values
    round-trip clean without mangering data that genuinely starts with one.
    """
    normalized = value.replace(CRLF, "\n")
    return normalized[1:] if normalized.startswith(" ") else normalized


def encode_sse_event(
    data: str,
    *,
    event: str | None = None,
    id: str | None = None,
    retry_ms: int | None = None,
) -> str:
    """Frame one event: field lines, multi-line data, the dispatching blank line.

    Multi-line ``data`` is emitted as one ``data:`` line per newline-separated
    piece — the client reassembles them with newlines, so the whole payload
    dispatches as ONE event, never several. The trailing blank line is what
    terminates the event; without it the client buffers forever.
    """
    lines: list[str] = []
    if event is not None:
        lines.append(f"{FIELD_EVENT}: {_single_line_value(event)}")
    if id is not None:
        lines.append(f"{FIELD_ID}: {_single_line_value(id)}")
    if retry_ms is not None:
        lines.append(f"{FIELD_RETRY}: {retry_ms}")
    for piece in _single_line_value(data).split("\n"):
        lines.append(f"data: {piece}")
    return "\n".join(lines) + "\n\n"


def encode_keepalive(comment: str = "keepalive") -> str:
    """Frame one comment event: ignored by clients, visible to proxies."""
    return f": {comment}\n\n"
