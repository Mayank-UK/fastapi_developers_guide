"""The app's CORS policy, stated once where both the wiring and the demo read it.

``create_app`` constructs Starlette's ``CORSMiddleware`` FROM these
constants, and the security lab panel SERVES them — so the demo can never
drift from the config it explains. The policy is the safe shape: an
EXPLICIT origin allow-list (the Vite dev server the guide's client runs
on) combined with ``allow_credentials`` — never the wildcard. ``*`` +
credentials is the classic misconfig: the spec forbids it outright for the
origin, and permissive middleware stacks "helpfully" answer by echoing ANY
requesting origin — which turns a credential-bearing browser into an open
proxy for whoever can make it send a cross-origin request.
"""

from typing import Final

from guide.core.serialization import CamelModel

ALLOWED_ORIGINS: Final[tuple[str, ...]] = ("http://localhost:5174",)
"""The exact origins allowed to make credentialed cross-origin calls.

Deliberately a LIST of explicit origins — the client dev server. Production
would list its real site origins here; nothing else changes."""

ALLOW_CREDENTIALS: Final[bool] = True
"""Cookies/Authorization may ride cross-origin calls — safe ONLY beside an
explicit origin list (the wildcard + credentials combination is the
misconfiguration; see ``cors_outcome``)."""

ALLOWED_METHODS: Final[tuple[str, ...]] = (
    "DELETE",
    "GET",
    "OPTIONS",
    "POST",
    "PUT",
)
"""The methods preflight approves; the guide's API surface, nothing more."""

ALLOWED_HEADERS: Final[tuple[str, ...]] = (
    "authorization",
    "content-type",
    "x-api-key",
    "x-request-id",
)
"""The request headers preflight approves — the credential slots the app
actually reads, instead of a blanket ``*``."""

PREFLIGHT_MAX_AGE_S: Final[int] = 600
"""How long a browser may cache one preflight answer (ten minutes)."""


class CorsOutcome(CamelModel):
    """What the configured policy answers for one asking origin.

    ``basis`` is the reason string — allowed names the matching entry;
    blocked states the default-deny rule, the same fail-closed posture as
    every other engine in the state-and-auth group.
    """

    origin: str
    allowed: bool
    basis: str


def cors_outcome(origin: str) -> CorsOutcome:
    """The REAL policy's verdict for an origin: allow-list hit, or deny.

    Exact-match only, like the browser-enforced ``Origin`` comparison and
    like Starlette's matcher — no substring surprises, no trailing-slash
    forgiveness. An empty origin (same-origin requests never send the
    header) is simply not a cross-origin question and reads as blocked.
    """
    if origin in ALLOWED_ORIGINS:
        return CorsOutcome(
            origin=origin,
            allowed=True,
            basis="exact match in the origin allow-list the app wires into CORSMiddleware",
        )
    return CorsOutcome(
        origin=origin,
        allowed=False,
        basis=(
            "not in the allow-list — the middleware adds no access-control-allow-origin "
            "header and answers preflights with 400 disallowed"
        ),
    )
