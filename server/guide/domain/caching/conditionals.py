"""HTTP conditional requests, as pure functions: ETag + If-None-Match.

The conditional endpoint's entire decision lives here, driver-free and
side-effect-free, so the endpoint itself stays a thin applicator and the
rules are testable to the letter of RFC 9110 section 13 (ETags) and
section 13.1.2 (If-None-Match). The ETag is a STRONG etag — a quoted
SHA-256 prefix over the exact payload bytes served — strong because the
bytes are the cache's own value: byte-identical means interchangeable.

``If-None-Match`` matching is weak by spec for GET: a client may send
``W/"abc"`` where the server said ``"abc"``, may send several candidates
comma-separated, and ``*`` matches anything the server currently has.
"""

import hashlib
from typing import Final

ETAG_HEX_LENGTH: Final = 16
"""SHA-256 prefix length — 64 bits of digest, collision-safe for one payload."""

RESPONSE_CACHE_CONTROL: Final = "no-cache"
"""The conditional endpoint's policy: store freely, but ALWAYS revalidate.

``no-cache`` is the honest pairing with ETag revalidation — it never
serves stale bytes without first asking the origin ``has this changed?``,
and ``If-None-Match`` is what makes that question cost 0 bytes of body
instead of a full payload. ``max-age`` (and its shared-cache sibling
``s-maxage``) serves WITHOUT asking — the right choice only when
freshness windows are acceptable, e.g. fingerprinted static assets."""


def compute_etag(payload: str) -> str:
    """A strong ETag over the payload's exact bytes: quoted SHA-256 prefix."""
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:ETAG_HEX_LENGTH]
    return f'"{digest}"'


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    """Does this ``If-None-Match`` header value name our current ETag?

    Absent header → False (not a conditional request). Present → split on
    commas, strip whitespace, compare WEAKLY (a leading ``W/`` on a
    candidate matches our strong etag — RFC 9110 allows weak comparison
    for GET). ``*`` matches any current representation.
    """
    if if_none_match is None:
        return False
    header = if_none_match.strip()
    if header == "*":
        return True
    candidates = (candidate.strip().removeprefix("W/") for candidate in header.split(","))
    return any(candidate == etag for candidate in candidates)
