"""Filename sanitizing: what survives when a user-supplied name meets a path.

The rule this module enforces is the path-traversal defense stated once for
the whole topic: USER INPUT NEVER BECOMES A PATH FRAGMENT UNCHECKED. When a
name must take part in a filesystem path at all, it first passes through
``sanitize_filename``, which is an ALLOW-LIST (keep only ``[A-Za-z0-9._-]``),
not a deny-list of known-bad spellings — deny-lists lose to encodings you did
not think of (``%2e%2e%2f`` after a decode layer, NFKC look-alikes, mixed
separators). The attacker's entire vocabulary is the characters that survive.

Every vector in the classic family dies the same boring death:

- ``../../etc/passwd`` — both separators are outside the allow-list, so the
  name collapses to ``etcpasswd``.
- ``..\\windows\\system32`` — backslash is just a filtered character here;
  it is a SEPARATOR on Windows, which is why deny-listing only ``/`` loses.
- ``/etc/passwd`` (absolute) — the leading separator is stripped with the
  rest, and the result can never re-acquire one.
- ``report\u202eevihcra.exe`` (unicode tricks) — non-ASCII is dropped, and
  with it every bidi-override and look-alike game.
- ``.hidden`` / ``..`` — a name that is only dots is rejected outright
  (None), because it means either the current directory or its parent.

``None`` (not an empty string) is the rejection answer: the caller maps it
to the standard ``validation_failed`` 422 envelope, never to a silent
fallback like ``"file"`` that would quietly accept hostile traffic.

The download path keeps the user's ORIGINAL display name for
``Content-Disposition`` (browsers want to show it) — that is safe because a
header value is encoded, not interpreted (see ``disposition.py``); a PATH
fragment is interpreted, so it gets this module. Data stays data; the path
is server-minted.
"""

import re
from typing import Final

ALLOWED_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9._-]")
"""The complement of the allow-list: everything this pattern matches is dropped."""

MAX_SANITIZED_LENGTH: Final[int] = 64
"""Cap a surviving name so no pathological input becomes a filesystem problem."""

MIN_SANITIZED_LENGTH: Final[int] = 1
"""Names shorter than this after filtering are rejections, not names."""


def sanitize_filename(name: str) -> str | None:
    """Reduce a user-supplied name to path-safe characters, or None if nothing honest survives.

    Pure and total: any string (empty, None-free by type, control characters,
    mixed separators, unicode of every script) maps to a compact ASCII slug
    or to ``None``. Leading dots are stripped after character filtering so
    ``.hidden`` and ``...`` cannot survive as dot-only names; a name that is
    ALL dots or all dropped characters has nothing honest left and returns
    ``None`` — the caller's signal to reject, not to invent a name.
    """
    stripped = ALLOWED_CHARACTERS.sub("", name)
    stripped = stripped.lstrip(".")
    trimmed = stripped[:MAX_SANITIZED_LENGTH].rstrip(".")
    if len(trimmed) < MIN_SANITIZED_LENGTH:
        return None
    return trimmed


def safe_join(root: str, user_fragment: str) -> str | None:
    """Join ``user_fragment`` under ``root`` ONLY if the resolved path stays inside it.

    The containment check the sanitizer makes belt-and-braces: ``resolve()``
    collapses every ``..`` and symlink spelling into the REAL absolute path,
    and the result must start with the resolved root's own path plus a
    separator — ``startswith(root)`` alone would admit ``/etc/passwd`` when
    the root is ``/etc/passwd-vault``. Returns None when the escape is
    attempted; the caller maps that to the 422 envelope.
    """
    from pathlib import Path

    resolved_root = Path(root).resolve()
    resolved = (resolved_root / user_fragment).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return str(resolved)
