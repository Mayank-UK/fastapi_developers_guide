"""The Range header, parsed and resolved: RFC 9110 semantics, pure functions.

A range request lets a client ask for PART of a representation — the resume
of an interrupted download, a video player scrubbing to a scene, a client
fetching one chunk of a large file at a time. The grammar (RFC 9110 §14)
is small but easy to get subtly wrong, so the whole thing lives here as
two pure steps the download endpoint composes:

1. ``parse_range_header`` — SYNTAX. ``bytes=0-99`` (first-spec, last-spec,
   both inclusive), ``bytes=100-`` (open-ended: start to EOF), and
   ``bytes=-100`` (suffix: the FINAL 100 bytes) are the three legal
   single-range spellings. Anything else — a missing ``bytes=`` unit, a
   non-numeric spec, ``start > end``, a zero-length suffix (``-0`` is
   defined as unsatisfiable, not as "nothing"), or a MULTI-range
   (``bytes=0-1,5-6``, which the RFC serves as multipart/byteranges when
   supported) — is invalid for this endpoint and returns None.

2. ``resolve_range`` — SEMANTICS against a known ``size``. Clamps an
   end past EOF back to the last byte (RFC: an end past the end means
   "through the end"), resolves a suffix to its absolute window (a suffix
   LONGER than the file resolves to the whole file, per the RFC), and
   returns None for an unsatisfiable range (a first-spec at or past EOF —
   the RFC's 416 case).

The deliberate divergence this module documents: RFC-strict servers answer
every invalid or unsatisfiable Range with 416 Range Not Satisfiable (and
 SHOULD ignore a syntactically invalid Range entirely, serving 200 full
body). This guide maps those rejections onto its ONE error taxonomy as
``validation_failed`` 422 envelopes — same shape as every other input
rejection — and the topic teaches the 416 form in prose so the divergence
is a decision on record, not an accident.
"""

from dataclasses import dataclass
from typing import Final

RANGE_UNIT: Final[str] = "bytes"
"""The one length unit this endpoint serves — byte ranges."""


@dataclass(frozen=True, slots=True)
class ParsedRange:
    """A syntactically valid single range: the raw window or a suffix length.

    ``last`` is inclusive (RFC grammar) and may be None for the open-ended
    ``start-`` form; ``suffix_length`` is set only for the ``-N`` form.
    """

    first: int
    last: int | None = None
    suffix_length: int | None = None


@dataclass(frozen=True, slots=True)
class ResolvedRange:
    """An absolute, clamped, satisfiable window: bytes [start, end] of total."""

    start: int
    end: int
    total: int

    @property
    def length(self) -> int:
        """The slice's byte count (end is inclusive)."""
        return self.end - self.start + 1

    @property
    def content_range(self) -> str:
        """The Content-Range header value a 206 must carry: ``bytes s-e/total``."""
        return f"bytes {self.start}-{self.end}/{self.total}"


def parse_range_header(value: str) -> ParsedRange | None:
    """Parse one Range header value; None when the syntax is invalid.

    Accepts exactly the three single-range spellings; surrounding whitespace
    is tolerated (the RFC allows it), every other deviation is a None so the
    endpoint can answer with the standard 422 envelope.
    """
    header = value.strip()
    if not header.startswith(f"{RANGE_UNIT}="):
        return None
    spec = header[len(f"{RANGE_UNIT}=") :].strip()
    if "," in spec:
        return None  # multi-range: unsupported here, taught in the topic
    if "-" not in spec:
        return None
    first_text, _, last_text = spec.partition("-")

    if first_text == "":  # the suffix form: bytes=-N
        if not last_text.isdigit():
            return None
        suffix_length = int(last_text)
        if suffix_length == 0:
            return None  # bytes=-0 is defined unsatisfiable
        return ParsedRange(first=0, suffix_length=suffix_length)

    if not first_text.isdigit():
        return None
    first = int(first_text)
    if last_text == "":  # the open-ended form: bytes=N-
        return ParsedRange(first=first, last=None)
    if not last_text.isdigit():
        return None
    last = int(last_text)
    if last < first:
        return None  # a last byte before the first is invalid by grammar
    return ParsedRange(first=first, last=last)


def resolve_range(parsed: ParsedRange, size: int) -> ResolvedRange | None:
    """Resolve a parsed range against a concrete size; None when unsatisfiable.

    Clamping rules (RFC 9110 §14.1.1): a last byte past EOF means "through
    the end"; a suffix longer than the representation resolves to the whole
    representation; a first byte at or past EOF is unsatisfiable (the 416
    case, surfaced here as None for the endpoint's 422 envelope).
    """
    if size == 0:
        return None  # no byte exists to satisfy any range

    if parsed.suffix_length is not None:
        start = max(0, size - parsed.suffix_length)
        return ResolvedRange(start=start, end=size - 1, total=size)

    if parsed.first >= size:
        return None
    end = parsed.last if parsed.last is not None else size - 1
    end = min(end, size - 1)
    return ResolvedRange(start=parsed.first, end=end, total=size)
