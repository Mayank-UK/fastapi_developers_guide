"""HTTP demo API: ``GET``/``POST /api/demo/http/headers`` — the echo pair.

Thin routers (family invariant): each handler collects the request facts the
pure builder needs and declares the echo response model. The POST variant
accepts an optional typed JSON body so a POST visibly carries a body (and a
``content-type``) that a GET cannot; the parsed ``message`` is echoed back,
closing the loop on what the server actually received. Absent facts are
omitted from the wire (``response_model_exclude_none`` — the family
convention), so a GET never serializes a null body message.
"""

from fastapi import APIRouter, Request

from guide.core.serialization import CamelModel
from guide.domain.demos.http_headers import HttpHeadersEchoPayload, build_http_headers_echo

router = APIRouter(prefix="/api/demo/http", tags=["demo:http"])


class HeadersDemoBody(CamelModel):
    """Optional POST body: a message the echo hands back unchanged."""

    message: str | None = None


def _echo(request: Request, body_message: str | None = None) -> HttpHeadersEchoPayload:
    """Collect the request facts once; the pure builder does the rest."""
    return build_http_headers_echo(
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        headers=request.headers,
        body_message=body_message,
    )


@router.get("/headers", response_model=HttpHeadersEchoPayload, response_model_exclude_none=True)
def read_headers_echo(request: Request) -> HttpHeadersEchoPayload:
    """Echo the GET exactly as the server received it."""
    return _echo(request)


@router.post(
    "/headers", response_model=HttpHeadersEchoPayload, response_model_exclude_none=True
)
def send_headers_echo(
    request: Request, body: HeadersDemoBody | None = None
) -> HttpHeadersEchoPayload:
    """Echo the POST — body parsed, content type reported, headers classified."""
    return _echo(request, body.message if body is not None else None)
