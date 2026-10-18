"""HTTP-headers demo payload: echo what the server actually received.

``GET`` and ``POST`` ``/api/demo/http/headers`` serve this payload. The
endpoint's whole point is honesty: it reports the request line the server
saw (method, path, raw query), the request's content type, and a selected,
normalized view of the inbound headers — the negotiation set (user-agent,
accept, accept-encoding, content-type), every ``x-*`` extension header, and
any hop-by-hop header that made it through the transport — each classified
end-to-end vs hop-by-hop. The canonical hop-by-hop reference list (RFC
9110 §7.6.1's closed set, plus HTTP/1.1's historic keep-alive) rides along
so the usual ABSENCE of ``Connection`` from a real server's echo is itself
the lesson: hop-by-hop headers belong to one transport connection and are
consumed before application code runs.

The builder is pure: plain data in, payload out — the router collects the
request facts, nothing else.
"""

from collections.abc import Mapping
from typing import Final, Literal

from guide.core.serialization import CamelModel

BASE_HEADER_SELECTION: Final[tuple[str, ...]] = (
    "user-agent",
    "accept",
    "accept-encoding",
    "content-type",
)
"""Negotiation/identity headers every echo reports when the client sent them."""

HOP_BY_HOP_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
"""RFC 9110 §7.6.1's closed set + HTTP/1.1's keep-alive: consumed per hop."""

_HEADER_NOTES: Final[dict[str, str]] = {
    "user-agent": "identifies the calling software; log it, rarely branch on it",
    "accept": "content negotiation: the media types this client will accept",
    "accept-encoding": "compression codings the client can decode (gzip, br, zstd)",
    "content-type": "the request body's media type — the contract the server parses by",
    "x-request-id": "correlation id: this guide's middleware echoes it or mints a fresh one",
    "connection": "hop-by-hop: describes this one transport connection, never forwarded",
}

HeaderScope = Literal["end-to-end", "hop-by-hop"]


class EchoedHeader(CamelModel):
    """One inbound header exactly as received, with its scope classification."""

    name: str
    value: str
    scope: HeaderScope
    note: str | None = None


class HttpHeadersEchoPayload(CamelModel):
    """Wire shape of the headers echo (camelCase; absent facts are omitted)."""

    method: str
    path: str
    query: str | None = None
    content_type: str | None = None
    body_message: str | None = None
    headers: list[EchoedHeader]
    hop_by_hop: list[str]


def _scope_for(name: str) -> HeaderScope:
    """Classify one header name against the RFC's hop-by-hop closed list."""
    return "hop-by-hop" if name in HOP_BY_HOP_HEADERS else "end-to-end"


def _note_for(name: str) -> str | None:
    """A one-line teaching note for known headers; None stays off the wire."""
    if name in _HEADER_NOTES:
        return _HEADER_NOTES[name]
    if name.startswith("x-"):
        return "extension header: the x- prefix is convention, not standard"
    return None


def _selected_names(received: Mapping[str, str]) -> list[str]:
    """Base headers in their fixed order first, then x-*/hop-by-hop sorted."""
    base = [name for name in BASE_HEADER_SELECTION if name in received]
    extras = sorted(
        name
        for name in received
        if name not in BASE_HEADER_SELECTION
        and (name.startswith("x-") or name in HOP_BY_HOP_HEADERS)
    )
    return base + extras


def build_http_headers_echo(
    *,
    method: str,
    path: str,
    query: str | None,
    headers: Mapping[str, str],
    body_message: str | None = None,
) -> HttpHeadersEchoPayload:
    """Build the echo payload from what the transport actually delivered."""
    received = {name.lower(): value for name, value in headers.items()}
    echoed = [
        EchoedHeader(
            name=name,
            value=received[name],
            scope=_scope_for(name),
            note=_note_for(name),
        )
        for name in _selected_names(received)
    ]
    return HttpHeadersEchoPayload(
        method=method,
        path=path,
        query=query or None,
        content_type=received.get("content-type"),
        body_message=body_message,
        headers=echoed,
        hop_by_hop=sorted(HOP_BY_HOP_HEADERS),
    )
