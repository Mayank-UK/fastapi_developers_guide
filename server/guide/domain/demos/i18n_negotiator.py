"""The i18n negotiator demo payload: the panel + the negotiation round.

Demo ``i18n:negotiator`` (topic 27, INLINE in the Accept-Language section):
one round IS the whole lesson — send an ``Accept-Language`` value (preset
or free-typed on the panel), and the response shows the header the server
actually received, the full ranked parse (every element's tag, q, and how
it matched), the negotiated locale, and then everything that locale does:
UI strings from the real catalog, CLDR formatting of the fixed inputs,
the plural counts with their CLDR categories, and the fixed instant on
three wall clocks. All pure shaping over the service's entities; no logic
lives here that the service didn't already decide.
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.i18n.catalog import CatalogEntry
from guide.domain.i18n.formatting import locale_display, plural_categories
from guide.domain.i18n.negotiation import NegotiationResult
from guide.domain.i18n.service import (
    DEMO_CURRENCY_AMOUNT,
    DEMO_CURRENCY_CODE,
    DEMO_INSTANT,
    DEMO_NUMBER,
    PLURAL_DEMO_COUNTS,
    I18nService,
    LocaleRendering,
)

NEGOTIATE_PATH: Final = "/api/demo/i18n/negotiate"
"""The one interactive endpoint — the panel and the terminal companion name it."""


class LocaleRow(CamelModel):
    """One servable locale: names and plural grammar from CLDR data."""

    tag: str
    english_name: str
    native_name: str
    plural_categories: list[str]


class CatalogCellRow(CamelModel):
    """One message in one catalog locale: what serves, and whether it fell back."""

    locale: str
    served: str
    translated: bool


class CatalogRow(CamelModel):
    """One message's row in the panel's catalog table (source beside translations)."""

    msgid: str
    translations: list[CatalogCellRow]


class I18nPolicyRow(CamelModel):
    """The demo's fixed facts: default locale, servable set, inputs, counts."""

    default_locale: str
    supported_locales: list[LocaleRow]
    fixed_instant: str
    number_input: float
    currency_code: str
    currency_amount: float
    plural_counts: list[int]


class EndpointRow(CamelModel):
    """One demo endpoint: the path and what trying it teaches."""

    path: str
    method: str
    teaches: str


class I18nPanel(CamelModel):
    """Wire shape of ``GET /api/demo/i18n`` — the panel's contract."""

    policy: I18nPolicyRow
    catalog: list[CatalogRow]
    endpoints: list[EndpointRow]
    honesty_notes: list[str]
    reasoning: str


class NegotiationRangeRow(CamelModel):
    """One element of the ranked parse: as sent, normalized, q, and its fate."""

    raw: str
    tag: str
    quality: float
    matched_locale: str | None
    matched_via: str


class UiStringRow(CamelModel):
    """One served UI string: the source message beside the localized value."""

    msgid: str
    value: str


class FormattingRow(CamelModel):
    """The fixed inputs rendered by the negotiated locale."""

    number_input: float
    number: str
    currency_code: str
    currency_amount: float
    currency: str
    instant: str
    date: str


class PluralRow(CamelModel):
    """One count: CLDR category beside the correctly pluralized sentence."""

    count: int
    category: str
    sentence: str


class ZoneRow(CamelModel):
    """The fixed instant on one wall clock, labeled by the negotiated locale."""

    zone: str
    wall_time: str
    utc_offset: str
    abbreviation: str
    formatted: str


class NegotiatorRound(CamelModel):
    """Wire shape of ``GET /api/demo/i18n/negotiate`` — one header, fully answered."""

    header: str | None
    selected_locale: str
    matched_via: str
    fell_back_to_default: bool
    ranges: list[NegotiationRangeRow]
    ui_strings: list[UiStringRow]
    formatting: FormattingRow
    plurals: list[PluralRow]
    zones: list[ZoneRow]


def build_locale_row(tag: str) -> LocaleRow:
    """One servable locale's display row (names and grammar from CLDR)."""
    english, native = locale_display(tag)
    return LocaleRow(
        tag=tag,
        english_name=english,
        native_name=native,
        plural_categories=list(plural_categories(tag)),
    )


def build_catalog_row(entry: CatalogEntry) -> CatalogRow:
    """Shape one catalog entry row (source message + per-locale cells)."""
    return CatalogRow(
        msgid=entry.msgid,
        translations=[
            CatalogCellRow(locale=tag, served=served, translated=translated)
            for tag, served, translated in entry.translations
        ],
    )


def build_i18n_panel(service: I18nService) -> I18nPanel:
    """Shape the panel: policy, the catalog table, the tour, honesty notes."""
    return I18nPanel(
        policy=I18nPolicyRow(
            default_locale=service.supported_locales()[0],
            supported_locales=[build_locale_row(tag) for tag in service.supported_locales()],
            fixed_instant=DEMO_INSTANT.isoformat(),
            number_input=DEMO_NUMBER,
            currency_code=DEMO_CURRENCY_CODE,
            currency_amount=DEMO_CURRENCY_AMOUNT,
            plural_counts=list(PLURAL_DEMO_COUNTS),
        ),
        catalog=[build_catalog_row(entry) for entry in service.catalog.entries()],
        endpoints=[
            EndpointRow(
                path=NEGOTIATE_PATH,
                method="GET",
                teaches=(
                    "send any Accept-Language (header) — ranked parse, locale, and "
                    "every layer it changes"
                ),
            ),
            EndpointRow(
                path="/api/content/internationalization",
                method="GET",
                teaches="this topic's own content — the terminal companion walks it too",
            ),
        ],
        honesty_notes=[
            "the .po catalogs are hand-written demo scope (real gettext files, real "
            "compilation); production catalogs come out of the extract→translate→"
            "compile→ship loop the workflow section teaches",
            "one German message ('Language') is deliberately untranslated — the "
            "fallback floor is the msgid itself, visible on the panel and in rounds",
            "the plural sentences come from gettext's ngettext over each catalog's "
            "own Plural-Forms header, and the category labels from babel's CLDR "
            "rules — two truth sources that agree on every integer count, pinned by test",
            "malformed Accept-Language elements are skipped, never errors: negotiation "
            "degrades to the default locale with the fallback visible in the payload",
        ],
        reasoning=(
            "The default API serves the world: negotiate the header, serve messages "
            "from real catalogs with a fallback chain, format numbers/currency/dates "
            "from CLDR data, pluralize by category math rather than singular/plural, "
            "and keep time as UTC instants that only become wall clocks at the edge."
        ),
    )


def build_negotiator_round(
    service: I18nService, negotiation: NegotiationResult, rendering: LocaleRendering
) -> NegotiatorRound:
    """Shape one negotiation round over the service's own entities."""
    return NegotiatorRound(
        header=negotiation.header,
        selected_locale=negotiation.selected,
        matched_via=negotiation.matched_via,
        fell_back_to_default=negotiation.fell_back_to_default,
        ranges=[
            NegotiationRangeRow(
                raw=row.parsed.raw,
                tag=row.parsed.tag,
                quality=row.parsed.quality,
                matched_locale=row.matched_locale,
                matched_via=row.matched_via,
            )
            for row in negotiation.rows
        ],
        ui_strings=[
            UiStringRow(msgid=msgid, value=value) for msgid, value in rendering.ui_strings
        ],
        formatting=FormattingRow(
            number_input=rendering.formatting.number_input,
            number=rendering.formatting.number,
            currency_code=rendering.formatting.currency_code,
            currency_amount=rendering.formatting.currency_amount,
            currency=rendering.formatting.currency,
            instant=rendering.formatting.instant.isoformat(),
            date=rendering.formatting.date,
        ),
        plurals=[
            PluralRow(count=plural.count, category=plural.category, sentence=plural.sentence)
            for plural in rendering.plurals
        ],
        zones=[
            ZoneRow(
                zone=zone_fact.zone_name,
                wall_time=zone_fact.wall_time.isoformat(),
                utc_offset=zone_fact.utc_offset,
                abbreviation=zone_fact.abbreviation,
                formatted=zone_fact.formatted,
            )
            for zone_fact in rendering.zones
        ],
    )
