"""Accept-Language negotiation: RFC 9110 §12.5.4 as one pure engine.

The header the browser sends on every request — ``Accept-Language:
de-DE,de;q=0.9,en;q=0.5`` — is a ranked wishlist, not a demand: each
comma-separated element is a language range carrying an optional quality
value (``q``, 0.000–1.000, default 1), the range ``*`` means "anything
else", and a ``q=0`` element means "explicitly not this". The server's job
is to walk that wishlist against the locales it ACTUALLY has and pick the
best mutual answer, falling back to its default locale when nothing
matches.

This module is that job, in two pure steps the demo router composes:

1. ``parse_accept_language`` — SYNTAX. Splits elements, normalizes tags to
   lowercase (BCP 47 tags are case-insensitive; ``de-DE`` and ``de-de`` are
   the same tag), reads the first ``q`` parameter, and SKIPS malformed
   elements instead of failing the request — a hostile or buggy client
   cannot make a bad header anyone's 500. Leniency rules, chosen and tested
   deliberately: a ``q`` that is not 0–1 with up to three decimals (``q=2``,
   ``q=abc``) is treated as absent (q=1), matching the RFC's spirit that
   unparseable metadata carries no information.

2. ``negotiate_locale`` — SEMANTICS against the supported set. Candidates
   are considered in q order (ties keep header order — the deterministic
   ordering), ``q=0`` elements are recorded as exclusions, and each
   candidate matches by exact tag, then by primary subtag (``de-DE`` →
   ``de``: the region fallback), with ``*`` matching the first supported
   locale no exclusion removed. No match anywhere means the default locale,
   flagged as a fallback so the demo can say WHY it answered in English.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

LanguageRange = Literal["exact", "region-fallback", "wildcard", "default"]
"""How the SELECTED locale was reached (``default`` = nothing matched)."""

RowMatch = Literal["exact", "region-fallback", "wildcard", "none", "excluded"]
"""How one parsed element fared: matched, unmatched, or removed by ``q=0``."""

_LANGUAGE_RANGE: Final[re.Pattern[str]] = re.compile(r"^\*|[a-z]{2,8}(-[a-z0-9]{1,8})*$")
"""A language range after lowercasing: ``*``, or an alpha primary subtag
(2–8 letters, BCP 47's language syntax) followed by alphanumeric subtags."""

_QVALUE: Final[re.Pattern[str]] = re.compile(r"^\d{1,3}(\.\d{0,3})?$")
"""RFC 9110 qvalue digits: up to three whole digits and up to three decimals."""


@dataclass(frozen=True, slots=True)
class ParsedLanguage:
    """One syntactically valid element of the header, position remembered.

    ``raw`` is the element as sent (the demo echoes it); ``tag`` is the
    normalized lowercase tag matching happens on; ``position`` preserves
    header order so equal-q candidates stay stable under sorting.
    """

    raw: str
    tag: str
    quality: float
    position: int


@dataclass(frozen=True, slots=True)
class NegotiationRow:
    """One element's fate, for the demo's ranked-parse display."""

    parsed: ParsedLanguage
    matched_locale: str | None
    matched_via: RowMatch


@dataclass(frozen=True, slots=True)
class NegotiationResult:
    """The whole negotiation: the answer plus every element's fate."""

    header: str | None
    selected: str
    matched_via: LanguageRange
    rows: tuple[NegotiationRow, ...]

    @property
    def fell_back_to_default(self) -> bool:
        """True when nothing matched and the default locale answered."""
        return self.matched_via == "default"


def parse_accept_language(header: str) -> tuple[ParsedLanguage, ...]:
    """Parse the header into valid elements; malformed elements are skipped.

    The empty string (and, by contract, ``None`` handled by the caller)
    parses to zero elements — an absent preference. Whitespace around
    elements and parameters is tolerated per the RFC's #rule syntax.
    """
    parsed: list[ParsedLanguage] = []
    for position, element in enumerate(header.split(",")):
        head, _, parameter_text = element.partition(";")
        raw = head.strip()
        if not raw:
            continue  # an empty element ("de,,en") carries no preference
        tag = raw.lower()
        if not _LANGUAGE_RANGE.match(tag):
            continue  # malformed range: skipped, never a crash
        parsed.append(
            ParsedLanguage(
                raw=raw,
                tag=tag,
                quality=_quality(parameter_text),
                position=position,
            )
        )
    return tuple(parsed)


def negotiate_locale(
    header: str | None, supported: Sequence[str], default: str
) -> NegotiationResult:
    """Pick the best supported locale for one header; pure and total.

    The default locale is the answer of last resort (absent header, no
    match, or every candidate excluded) — and the wildcard's answer too,
    unless an exclusion removed it, in which case the first surviving
    supported locale serves (``en;q=0, *`` is "anything but English").
    """
    lowered = {tag.lower(): tag for tag in supported}
    elements = parse_accept_language(header) if header else ()

    excluded = {
        locale
        for element in elements
        if element.quality == 0.0
        for locale in (_exact_match(element.tag, lowered),)
        if locale is not None
    }
    if any(element.tag == "*" and element.quality == 0.0 for element in elements):
        excluded.update(lowered.values())  # ``*;q=0`` excludes everything

    candidates = sorted(
        (element for element in elements if element.quality > 0.0),
        key=lambda element: (-element.quality, element.position),
    )

    rows: list[NegotiationRow] = []
    selected: str | None = None
    selected_via: LanguageRange = "default"
    for element in candidates:
        if element.tag == "*":
            pick = next(
                (tag for tag in supported if tag.lower() not in excluded), None
            )
            if pick is not None and selected is None:
                selected, selected_via = pick, "wildcard"
            rows.append(
                NegotiationRow(
                    parsed=element, matched_locale=pick, matched_via="wildcard"
                )
            )
            continue
        exact = _exact_match(element.tag, lowered)
        if exact is not None and exact not in excluded:
            if selected is None:
                selected, selected_via = exact, "exact"
            rows.append(
                NegotiationRow(parsed=element, matched_locale=exact, matched_via="exact")
            )
            continue
        primary = element.tag.split("-", 1)[0]
        regional = _exact_match(primary, lowered)
        if regional is not None and regional not in excluded:
            if selected is None:
                selected, selected_via = regional, "region-fallback"
            rows.append(
                NegotiationRow(
                    parsed=element, matched_locale=regional, matched_via="region-fallback"
                )
            )
            continue
        rows.append(NegotiationRow(parsed=element, matched_locale=None, matched_via="none"))

    for element in elements:
        if element.quality == 0.0:
            rows.append(
                NegotiationRow(
                    parsed=element,
                    matched_locale=_exact_match(element.tag, lowered),
                    matched_via="excluded",
                )
            )

    if selected is None:
        selected = default
    return NegotiationResult(
        header=header,
        selected=selected,
        matched_via=selected_via,
        rows=tuple(rows),
    )


def _exact_match(tag: str, lowered: dict[str, str]) -> str | None:
    """The supported locale for a tag, case-insensitively, or None."""
    return lowered.get(tag) if tag != "*" else None


def _quality(parameter_text: str) -> float:
    """The first parseable q parameter's value; 1.0 when none qualifies.

    ``q=2`` and ``q=abc`` are RFC-invalid — treated as absent (1.0), the
    documented leniency: unparseable metadata carries no information.
    """
    for parameter in parameter_text.split(";"):
        name, separator, value = parameter.partition("=")
        if separator and name.strip().lower() == "q" and _QVALUE.match(value.strip()):
            parsed = float(value)
            return parsed if 0.0 <= parsed <= 1.0 else 1.0
    return 1.0
