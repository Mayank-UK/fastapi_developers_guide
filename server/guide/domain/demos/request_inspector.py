"""Request-inspector demo payload: the live Request object, made observable.

``GET`` and ``POST`` ``/api/demo/reqres/inspector`` serve this payload. The
demo's point is honesty about the view a handler actually gets: Starlette's
``Request`` is a parsed window onto the raw ASGI scope, and this builder
mirrors the facts that window exposes — the request line (method, path, raw
query), the query parsed with EVERY occurrence preserved (so ``?tag=a&tag=b``
shows up as one key holding two values — the multi-value behavior a
``list[str]`` annotation collects and a plain ``str`` collapses to the
last), a selected view of the inbound headers, the body contract
(content type + content length + the parsed message on POST), the
transport's idea of the client address, and the request id the middleware
assigned two layers out in the onion before any endpoint code ran.

The builder is pure: the router collects the facts from the live
``Request`` and passes them in as plain data; nothing here touches the
app, the clock, or the network.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from guide.core.request_context import REQUEST_ID_HEADER
from guide.core.serialization import CamelModel

INSPECTED_HEADERS: Final[tuple[str, ...]] = (
    "user-agent",
    "accept",
    "accept-encoding",
    "content-type",
    "content-length",
    "x-request-id",
)
"""The fixed selection the payload reports, in this order, when present."""


class QueryParamView(CamelModel):
    """One query key with every value the caller sent for it."""

    name: str
    values: list[str]
    is_repeated: bool


class SeenHeader(CamelModel):
    """One selected inbound header exactly as the Request reports it."""

    name: str
    value: str


class ClientAddress(CamelModel):
    """The transport's peer address as the ASGI scope carries it."""

    host: str
    port: int


class RequestInspectorPayload(CamelModel):
    """Wire shape of the inspector (camelCase; absent facts are omitted)."""

    method: str
    path: str
    raw_query: str | None = None
    query_params: list[QueryParamView]
    headers: list[SeenHeader]
    content_type: str | None = None
    content_length: int | None = None
    body_message: str | None = None
    client: ClientAddress | None = None
    request_id: str
    request_id_header: str
    reasoning: str


def _parse_content_length(raw: str | None) -> int | None:
    """Parse the inbound content-length defensively; garbage reads as absent."""
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def _selected_header_names(received: Mapping[str, str]) -> list[str]:
    """The fixed selection first (present ones), then remaining x-* sorted."""
    base = [name for name in INSPECTED_HEADERS if name in received]
    extras = sorted(
        name for name in received if name not in INSPECTED_HEADERS and name.startswith("x-")
    )
    return base + extras


def build_request_inspector_payload(
    *,
    method: str,
    path: str,
    raw_query: str | None,
    query_pairs: Sequence[tuple[str, str]],
    headers: Mapping[str, str],
    client_host: str | None,
    client_port: int | None,
    request_id: str,
    body_message: str | None = None,
) -> RequestInspectorPayload:
    """Reflect the request's own facts back as the inspector payload (pure)."""
    collected: dict[str, list[str]] = {}
    for name, value in query_pairs:
        collected.setdefault(name, []).append(value)
    query_params = [
        QueryParamView(name=name, values=values, is_repeated=len(values) > 1)
        for name, values in collected.items()
    ]
    received = {name.lower(): value for name, value in headers.items()}
    seen_headers = [
        SeenHeader(name=name, value=received[name]) for name in _selected_header_names(received)
    ]
    repeated = [param.name for param in query_params if param.is_repeated]
    repeated_note = (
        f" Keys repeated on the wire ({', '.join(repeated)}) collect every "
        "occurrence — a list[str] annotation binds them all, a plain str "
        "takes the last."
        if repeated
        else ""
    )
    reasoning = (
        f"This payload is the handler's own view of the {method} request that "
        "fetched it: the Request object parsed the request line, the query "
        "string, and the headers before any endpoint code ran, and the "
        f"request-id middleware had already assigned {request_id!r} two "
        f"layers out in the onion (topic 08). The response echoing this "
        f"payload carries the same id on its {REQUEST_ID_HEADER} header — "
        "stamped after the payload was serialized, so curl -i can watch both "
        f"sides agree.{repeated_note}"
    )
    return RequestInspectorPayload(
        method=method,
        path=path,
        raw_query=raw_query or None,
        query_params=query_params,
        headers=seen_headers,
        content_type=received.get("content-type"),
        content_length=_parse_content_length(received.get("content-length")),
        body_message=body_message,
        client=(
            ClientAddress(host=client_host, port=client_port)
            if client_host is not None and client_port is not None
            else None
        ),
        request_id=request_id,
        request_id_header=REQUEST_ID_HEADER,
        reasoning=reasoning,
    )
