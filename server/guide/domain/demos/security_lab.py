"""The security lab demo payload: headers + CORS + rate limiting, derived purely.

``build_security_lab_panel`` shapes the panel topic 25's ``security:lab``
serves INLINE in the headers section: the security-header documentation
table straight from the middleware that enforces it, the REAL CORS policy
(the same constants ``create_app`` wires into ``CORSMiddleware``), and the
burner endpoint's rate-limit policy (the same numbers the live limiter
holds). Nothing here invents configuration — the panel quotes the three
sources of truth, so the demo cannot drift from the app it explains.

``build_burn_row`` shapes one successful burn round; the EXHAUSTED round
never reaches a builder — the dependency raises the standard 429 envelope
with ``Retry-After``, which is exactly the outcome the lab teaches.
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.security.cors import (
    ALLOW_CREDENTIALS,
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
    ALLOWED_ORIGINS,
    PREFLIGHT_MAX_AGE_S,
)
from guide.domain.security.rate_limit import RateLimitPolicy, RateLimitVerdict
from guide.presentation.middleware.security_headers import SECURITY_HEADER_NOTES

BURN_PATH: Final = "/api/demo/security/rate-limit/burn"
"""The lab's burnable endpoint — public on purpose (it is the lesson)."""


class HeaderNoteRow(CamelModel):
    """One security header: name, the value the middleware stamps, and why."""

    header: str
    value: str
    why: str


class CorsPanelRow(CamelModel):
    """The REAL CORS policy the app runs — the constants the wiring reads."""

    allowed_origins: tuple[str, ...]
    allow_credentials: bool
    allowed_methods: tuple[str, ...]
    allowed_headers: tuple[str, ...]
    preflight_max_age_s: int
    misconfig_note: str


class RateLimitPanelRow(CamelModel):
    """The burner's real policy: window, budget, keying, and the endpoint."""

    window_seconds: float
    budget: int
    keying: str
    burn_endpoint: str
    why_public_endpoints: str


class SecurityLabPanel(CamelModel):
    """Wire shape of ``GET /api/demo/security`` — the lab panel's contract."""

    headers: list[HeaderNoteRow]
    cors: CorsPanelRow
    rate_limit: RateLimitPanelRow
    reasoning: str


class BurnRow(CamelModel):
    """Wire shape of a successful burn: the budget as it now stands."""

    attempt: int
    remaining: int
    limit: int
    window_seconds: float
    detail: str


def build_security_lab_panel(policy: RateLimitPolicy) -> SecurityLabPanel:
    """Shape the panel (pure) from the three real sources of truth."""
    return SecurityLabPanel(
        headers=[
            HeaderNoteRow(header=note.header, value=note.value, why=note.why)
            for note in SECURITY_HEADER_NOTES
        ],
        cors=CorsPanelRow(
            allowed_origins=ALLOWED_ORIGINS,
            allow_credentials=ALLOW_CREDENTIALS,
            allowed_methods=ALLOWED_METHODS,
            allowed_headers=ALLOWED_HEADERS,
            preflight_max_age_s=PREFLIGHT_MAX_AGE_S,
            misconfig_note=(
                "wildcard origins with credentials is the classic misconfig: the "
                "spec forbids '*' with credentials, and permissive stacks answer "
                "by echoing ANY origin — this app pairs credentials with an "
                "explicit list instead"
            ),
        ),
        rate_limit=RateLimitPanelRow(
            window_seconds=policy.window_s,
            budget=policy.budget,
            keying=policy.keying,
            burn_endpoint=BURN_PATH,
            why_public_endpoints=(
                "endpoints that check no credential — logins, health, this burner "
                "— are the ones anyone may hammer; the limiter is the only brake "
                "they have"
            ),
        ),
        reasoning=(
            "Three defaults with teeth: every response carries the security "
            "headers (error envelopes included — they are the responses an "
            "attacker probes), CORS answers from an explicit origin list never a "
            "wildcard, and the public burner holds a real sliding-window budget "
            "that answers 429 with Retry-After when it runs dry."
        ),
    )


def build_burn_row(verdict: RateLimitVerdict) -> BurnRow:
    """Shape one allowed burn — the attempt number follows from the verdict."""
    return BurnRow(
        attempt=verdict.limit - verdict.remaining,
        remaining=verdict.remaining,
        limit=verdict.limit,
        window_seconds=verdict.window_s,
        detail=(
            f"{verdict.remaining} of {verdict.limit} left in this "
            f"{verdict.window_s:g}s window — keep burning to watch it run out"
            if verdict.remaining > 0
            else "budget exhausted — the next hit is the 429 envelope with Retry-After"
        ),
    )
