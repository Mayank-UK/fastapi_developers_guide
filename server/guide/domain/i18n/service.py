"""The i18n service: negotiation, catalog, formatting, and zones in one place.

Everything the demo router calls, in the domain, so the router stays thin
(the family invariant): ``negotiate`` turns one ``Accept-Language`` header
into the selected locale plus every element's fate; ``render`` turns one
locale into the full localized exhibit — UI strings through the real
catalog, number/currency/date through CLDR, the plural counts through the
category math, and the fixed instant across the demo's three wall clocks.
``render`` answers in the NEGOTIATED locale, which is the point: one
round shows what one header did to every layer at once.

There is no error path here by design — a malformed header is not an
error (the negotiation engine skips bad elements and may fall back to the
default locale, with the fallback VISIBLE in the result), and every
formatting input is a domain constant, not client input. The one raising
surface is an unknown IANA zone name, which the router surfaces as the
standard validation envelope.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from guide.domain.i18n.catalog import DEFAULT_LOCALE, UI_MESSAGES, MessageCatalog
from guide.domain.i18n.formatting import (
    format_currency,
    format_instant,
    format_number,
    plural_category,
)
from guide.domain.i18n.negotiation import NegotiationResult, negotiate_locale
from guide.domain.i18n.timezones import (
    WALL_CLOCK_ZONES,
    render_wall_clock,
    wall_clock,
)

DEMO_INSTANT: Final[datetime] = datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
"""The fixed instant every formatting row renders.

Deliberately chosen: 2026-03-08 07:30 UTC is ninety minutes after New
York's spring-forward jump (02:00 EST → 03:00 EDT), so the zone panel
shows a DST-shifted wall (03:30 EDT) beside UTC and Kolkata — pinned,
machine-independent, and pedagogically loaded all at once.
"""

DEMO_NUMBER: Final[float] = 1234567.89
DEMO_CURRENCY_CODE: Final[str] = "EUR"
DEMO_CURRENCY_AMOUNT: Final[float] = 1234.5
PLURAL_DEMO_COUNTS: Final[tuple[int, ...]] = (0, 1, 2, 5, 22)
"""The formatting inputs and the plural counts — one set, every locale."""


@dataclass(frozen=True, slots=True)
class FormattingFacts:
    """One locale's formatting of the fixed inputs: in-data and rendered."""

    number_input: float
    number: str
    currency_code: str
    currency_amount: float
    currency: str
    instant: datetime
    date: str


@dataclass(frozen=True, slots=True)
class PluralFact:
    """One count's plural verdict: the CLDR category beside the sentence."""

    count: int
    category: str
    sentence: str


@dataclass(frozen=True, slots=True)
class ZoneFact:
    """The fixed instant on one wall, labeled by the rendering locale."""

    zone_name: str
    wall_time: datetime
    utc_offset: str
    abbreviation: str
    formatted: str


@dataclass(frozen=True, slots=True)
class LocaleRendering:
    """One locale fully rendered — the demo round's domain payload."""

    locale: str
    ui_strings: tuple[tuple[str, str], ...]
    formatting: FormattingFacts
    plurals: tuple[PluralFact, ...]
    zones: tuple[ZoneFact, ...]


class I18nService:
    """Negotiates and renders, over the compiled catalog and pure engines."""

    def __init__(
        self,
        catalog: MessageCatalog,
        zone_names: Sequence[str] = WALL_CLOCK_ZONES,
        fixed_instant: datetime = DEMO_INSTANT,
    ) -> None:
        """Hold the wiring the composition root chose (one set per app)."""
        self._catalog = catalog
        self._zone_names = tuple(zone_names)
        self._fixed_instant = fixed_instant

    @property
    def catalog(self) -> MessageCatalog:
        """The compiled catalog (the panel's entries read through it)."""
        return self._catalog

    @property
    def fixed_instant(self) -> datetime:
        """The instant every zone row renders (echoed on the panel)."""
        return self._fixed_instant

    def supported_locales(self) -> tuple[str, ...]:
        """The servable locale tags: default first, catalog locales after."""
        return self._catalog.locales()

    def negotiate(self, accept_language: str | None) -> NegotiationResult:
        """Run the header through the engine against the servable set."""
        return negotiate_locale(accept_language, self.supported_locales(), DEFAULT_LOCALE)

    def render(self, locale: str) -> LocaleRendering:
        """One locale's full exhibit, every layer in that locale.

        Pure in ``locale`` and the construction-fixed inputs; the same
        locale always renders identically, which is what lets the tests
        pin exact strings and the panel promise reproducible output.
        """
        return LocaleRendering(
            locale=locale,
            ui_strings=tuple(
                (msgid, self._catalog.translate(locale, msgid)) for msgid in UI_MESSAGES
            ),
            formatting=FormattingFacts(
                number_input=DEMO_NUMBER,
                number=format_number(DEMO_NUMBER, locale),
                currency_code=DEMO_CURRENCY_CODE,
                currency_amount=DEMO_CURRENCY_AMOUNT,
                currency=format_currency(DEMO_CURRENCY_AMOUNT, DEMO_CURRENCY_CODE, locale),
                instant=self._fixed_instant,
                date=format_instant(self._fixed_instant, locale),
            ),
            plurals=tuple(
                PluralFact(
                    count=count,
                    category=plural_category(locale, count),
                    sentence=self._catalog.plural_sentence(locale, count),
                )
                for count in PLURAL_DEMO_COUNTS
            ),
            zones=tuple(
                ZoneFact(
                    zone_name=zone_name,
                    wall_time=wall,
                    utc_offset=offset,
                    abbreviation=abbreviation,
                    formatted=render_wall_clock(self._fixed_instant, zone_name, locale),
                )
                for zone_name in self._zone_names
                for wall, offset, abbreviation in (wall_clock(self._fixed_instant, zone_name),)
            ),
        )
