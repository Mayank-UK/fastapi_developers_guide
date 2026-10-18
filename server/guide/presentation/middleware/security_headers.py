"""Security-headers middleware: every response — including error envelopes.

Topic 25's headers section as code. ``SecurityHeadersMiddleware`` stamps
the defensive response headers the app owes on EVERY response, because the
error paths are the ones attackers actually probe: a 404 that skips
``X-Content-Type-Options`` is the response most likely to be rendered by
some intermediary. The middleware wraps the stack inside CORS (added
after it in ``create_app``), so even envelope responses carry both the
CORS verdict and these headers.

Two deliberate scope decisions, both teachable. First, the CSP is
PATH-AWARE: the API answers a strict ``default-src 'none'`` (a JSON
endpoint loads nothing and should be unable to), while the docs pages —
which legitimately load Swagger UI/ReDoc assets from the CDN and run an
inline bootstrap — get a policy that permits exactly those sources. One
global permissive policy would have been simpler and strictly worse.
Second, HSTS is TLS-ONLY: it is stamped when the request itself arrived
over https (production terminates TLS at the proxy, and the proxy is where
this header belongs) and withheld in dev, where plain-http HSTS is ignored
by browsers anyway — sending it would be claiming a property the
connection does not have.

The ``SECURITY_HEADER_NOTES`` table (header → value → why) is the single
source the demo panel serves, so the documentation can never drift from
the middleware that enforces it.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

API_CSP: Final = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
"""The API's CSP: load nothing, embed nowhere, navigate nowhere — a JSON
endpoint's content security policy is a refusal."""

DOCS_CSP: Final = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'"
)
"""The docs pages' CSP: exactly what Swagger UI/ReDoc need — the CDN's
scripts and styles plus their inline bootstrap — and nothing more."""

HSTS_HEADER: Final = "Strict-Transport-Security"
HSTS_VALUE: Final = "max-age=31536000; includeSubDomains"
"""One year of https-only, subdomains included. TLS-ONLY by design: the
middleware stamps it just when the request arrived over https; over plain
http (dev) the header would be both ignored by browsers and dishonest
about the connection. Production usually stamps it at the TLS proxy."""

_DOCS_PATHS: Final[frozenset[str]] = frozenset(
    {"/docs", "/docs/oauth2-redirect", "/redoc"}
)
"""The HTML surfaces FastAPI mounts — the paths that earn the docs CSP."""

_STATIC_HEADERS: Final[dict[str, str]] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": API_CSP,
}
"""The headers every response starts from; CSP is overridden on docs paths."""


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Stamp the defensive headers on every response, errors included."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Forward the request, then stamp headers on whatever comes back."""
        response = await call_next(request)
        for name, value in _STATIC_HEADERS.items():
            response.headers[name] = value
        if request.url.path in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = DOCS_CSP
        if request.url.scheme == "https":
            response.headers[HSTS_HEADER] = HSTS_VALUE
        return response


@dataclass(frozen=True, slots=True)
class SecurityHeaderNote:
    """One documentation row: the header, its value, and WHY it is sent."""

    header: str
    value: str
    why: str


SECURITY_HEADER_NOTES: Final[tuple[SecurityHeaderNote, ...]] = (
    SecurityHeaderNote(
        header="X-Content-Type-Options",
        value="nosniff",
        why=(
            "the browser must not second-guess the content type — without this, "
            "a JSON response a proxy mislabels as text/html can execute as a page"
        ),
    ),
    SecurityHeaderNote(
        header="X-Frame-Options",
        value="DENY",
        why=(
            "no iframe may embed the app — clickjacking needs your real UI in "
            "someone else's frame, and DENY closes the door the CSP also guards"
        ),
    ),
    SecurityHeaderNote(
        header="Referrer-Policy",
        value="no-referrer",
        why=(
            "outbound links learn nothing about where they came from — API paths "
            "carry ids and tokens in query strings nobody should leak onward"
        ),
    ),
    SecurityHeaderNote(
        header="Content-Security-Policy",
        value=API_CSP,
        why=(
            "the API loads nothing, so its CSP is default-src 'none' — even an "
            "injected script tag finds no source it is allowed to load from; "
            "the docs pages get a policy permitting exactly their CDN assets"
        ),
    ),
    SecurityHeaderNote(
        header=HSTS_HEADER,
        value=f"{HSTS_VALUE} — https requests only",
        why=(
            "after one https visit, the browser refuses plain http to this host "
            "for a year; sent only over https because over http it is ignored "
            "by browsers and dishonest about the connection (dev is http)"
        ),
    ),
)
"""The WHY table — served by the security lab panel straight from the
middleware that enforces it, so docs and behavior cannot drift."""
