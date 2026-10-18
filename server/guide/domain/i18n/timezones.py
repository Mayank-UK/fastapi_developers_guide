"""Timezones: the wall-clock half of the two-axis model, over zoneinfo.

A timezone and a locale answer DIFFERENT questions. The zone says what a
shared INSTANT reads on a particular wall clock — the same moment is
``07:30`` in UTC, ``03:30`` in New York (after the spring-forward jump),
``13:00`` in Kolkata (a half-hour offset zone). The locale says how any
wall time is LABELED — month names, ordering, separators (``formatting.py``).
Conflating them is the classic bug: "German" does not imply "Berlin's
clock", and "UTC storage" does not imply "American-formatted output".

This module is stdlib ``zoneinfo`` behind typed, pure functions: convert
one aware instant into a zone's wall clock (offset and abbreviation
included, computed from the zone's own rules — DST transitions and
half-hour offsets come out right because the IANA database is the
authority), and render a wall-clock string through the formatting layer.
Storage discipline rides in the callers: instants are stored UTC and
zoned only at the edge, exactly as the topic teaches.
"""

from datetime import datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from guide.domain.i18n.formatting import format_instant

WALL_CLOCK_ZONES: Final[tuple[str, ...]] = ("UTC", "America/New_York", "Asia/Kolkata")
"""The demo's three walls: the reference, a DST-jumping zone, a half-hour zone."""


class UnknownZoneError(ValueError):
    """An IANA zone name zoneinfo does not know (surfaced as a domain fact)."""

    def __init__(self, zone_name: str) -> None:
        super().__init__(f"unknown IANA timezone {zone_name!r}")
        self.zone_name = zone_name


def zone(zone_name: str) -> ZoneInfo:
    """The ZoneInfo for an IANA name; unknown names raise, never guess."""
    try:
        return ZoneInfo(zone_name)
    except (KeyError, ValueError) as error:
        raise UnknownZoneError(zone_name) from error


def wall_clock(instant: datetime, zone_name: str) -> tuple[datetime, str, str]:
    """One instant on one wall: (wall time, UTC offset, abbreviation).

    The instant must be timezone-aware (the model's left axis); the wall
    time is what that zone's clocks read, the offset is ISO-style
    ``+05:30``, and the abbreviation (``UTC``, ``EDT``, ``IST``) comes
    from the zone's own rules at that moment.
    """
    if instant.tzinfo is None:
        raise ValueError("wall_clock needs an aware instant — store and pass UTC")
    local = instant.astimezone(zone(zone_name))
    return local, utc_offset_text(local), local.tzname() or zone_name


def render_wall_clock(instant: datetime, zone_name: str, locale_tag: str) -> str:
    """The wall time in a zone, labeled by a locale (the two axes crossing)."""
    return format_instant(instant.astimezone(zone(zone_name)), locale_tag)


def utc_offset_text(local: datetime) -> str:
    """An ISO-8601 style UTC offset (``+05:30``) for a zoned wall time."""
    offset = local.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds()) // 60
    sign = "+" if minutes >= 0 else "-"
    hours, remainder = divmod(abs(minutes), 60)
    return f"{sign}{hours:02d}:{remainder:02d}"
