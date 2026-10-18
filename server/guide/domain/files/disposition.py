"""Content-Disposition, built safely: RFC 6266 semantics, RFC 5987 encoding.

The header that decides what a browser DOES with a download: ``inline``
(the payload renders — images, PDFs, text) versus ``attachment`` (save to
disk). Without it the browser guesses from the Content-Type, and a guessed
``inline`` on attacker-influenced bytes is how HTML uploads become stored
XSS on your origin — setting the header explicitly, with ``attachment`` as
the default for anything not provably renderable, removes the guess.

Filenames are the subtle half. RFC 6266 sends the ASCII-safe name in the
``filename`` parameter and, for every name outside that alphabet (and for
names with characters parameter syntax cares about), a percent-encoded
UTF-8 form in ``filename*`` (the RFC 5987 extended parameter) — browsers
prefer ``filename*`` when present, and older clients fall back to
``filename``. A non-ASCII name like ``拍data.txt`` therefore travels as
both ``filename="data.txt"``-shaped ASCII residue and the exact bytes in
``filename*=UTF-8''%E6%8B%8Ddata.txt``.

Header injection is the attack this module refuses: a CR or LF inside a
filename would, on naive string concatenation, split the header and forge
new ones (``Set-Cookie``, say). ``clean_display_name`` strips every control
character BEFORE the name is quoted, so the builder's output is a single
header line by construction — defense at the boundary, not a deny-list of
header names downstream.
"""

import urllib.parse
from typing import Final

INLINE: Final[str] = "inline"
ATTACHMENT: Final[str] = "attachment"
"""The two disposition types — the workbench's download toggle."""

ASCII_SAFE: Final[frozenset[str]] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "!#$%&+-.^_`|~"
)
"""Characters safe un-quoted in a parameter token; quotes/semicolons force quoting."""

MAX_DISPLAY_NAME_LENGTH: Final[int] = 128
"""Cap a display name — a filename is metadata, not a document."""


def clean_display_name(name: str) -> str:
    """Strip control characters (CR/LF injection among them) and cap length.

    The download path's first touch of a stored name: an HTTP header value
    must be one line, so every C0 control character is removed before the
    name is ever placed in a header — ``evil\r\nSet-Cookie: …`` collapses
    to ``evilSet-Cookie: …``, inert inside a quoted parameter.
    """
    cleaned = "".join(char for char in name if ord(char) >= 0x20 and ord(char) != 0x7F)
    return cleaned.strip()[:MAX_DISPLAY_NAME_LENGTH]


def _quote_ascii(ascii_name: str) -> str:
    """Quote an ASCII parameter value, escaping inner quotes and backslashes."""
    escaped = ascii_name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_content_disposition(disposition_type: str, display_name: str) -> str:
    """Build the header value: type, ASCII ``filename``, and ``filename*`` when needed.

    Pure string building over a cleaned name. The ASCII parameter carries
    the name's ASCII residue (or the whole name when it is already ASCII);
    the RFC 5987 extended parameter is added whenever the name holds
    non-ASCII or quoting-hostile characters, percent-encoded as UTF-8 —
    the exact pair real download servers emit.
    """
    name = clean_display_name(display_name) or "download"
    ascii_only = name.isascii()
    ascii_name = name if ascii_only else _ascii_residue(name)
    parts = [disposition_type, f"filename={_quote_ascii(ascii_name)}"]
    if not ascii_only:
        encoded = urllib.parse.quote(name, safe="", encoding="utf-8")
        parts.append(f"filename*=UTF-8''{encoded}")
    return "; ".join(parts)


def _ascii_residue(name: str) -> str:
    """The name with non-ASCII runs collapsed to underscores — the fallback name."""
    residue: list[str] = []
    previous_was_dropped = False
    for char in name:
        if char.isascii():
            residue.append(char)
            previous_was_dropped = False
        elif not previous_was_dropped:
            residue.append("_")
            previous_was_dropped = True
    fallback = "".join(residue).strip("_") or "download"
    return fallback
