"""The i18n engines (topic 27): negotiation table, catalog chain, CLDR, zones.

Deterministic by construction: every formatting assertion pins exact
strings for fixed inputs (babel's data ships with the locked version; no
machine locale or timezone is consulted — the fixed instant is UTC-aware
and every zone conversion goes through zoneinfo against the IANA
database), and the negotiation table covers the engine's whole contract:
absent/empty headers, wildcards, q=0 exclusions, case-insensitivity,
region fallback, malformed elements skipped, junk q-values, duplicates,
and the stable q-ordering with header-order tie-breaks.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from guide.domain.i18n.catalog import (
    DEFAULT_LOCALE,
    MessageCatalog,
    compile_mo_bytes,
)
from guide.domain.i18n.formatting import (
    format_currency,
    format_instant,
    format_number,
    plural_categories,
    plural_category,
)
from guide.domain.i18n.negotiation import negotiate_locale, parse_accept_language
from guide.domain.i18n.service import DEMO_INSTANT, I18nService
from guide.domain.i18n.timezones import (
    UnknownZoneError,
    render_wall_clock,
    utc_offset_text,
    wall_clock,
)

SUPPORTED = ("en", "de", "pl")


# ── negotiation: the parse table ────────────────────────────────────────────


def test_absent_and_empty_headers_parse_to_nothing() -> None:
    assert negotiate_locale(None, SUPPORTED, DEFAULT_LOCALE).selected == "en"
    assert negotiate_locale("", SUPPORTED, DEFAULT_LOCALE).selected == "en"
    result = negotiate_locale("", SUPPORTED, DEFAULT_LOCALE)
    assert result.fell_back_to_default and result.rows == ()
    assert result.header == ""


def test_wildcard_matches_the_default_locale() -> None:
    result = negotiate_locale("*", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "en"
    assert result.matched_via == "wildcard"
    assert [row.matched_via for row in result.rows] == ["wildcard"]


def test_wildcard_q_zero_excludes_everything() -> None:
    result = negotiate_locale("*;q=0", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "en"
    assert result.fell_back_to_default
    assert [row.matched_via for row in result.rows] == ["excluded"]


def test_wildcard_honors_named_exclusions() -> None:
    # "anything but English" — the wildcard serves the first survivor.
    result = negotiate_locale("en;q=0, *", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "de"
    assert result.matched_via == "wildcard"


def test_tags_are_case_insensitive() -> None:
    result = negotiate_locale("PL", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "pl"
    assert result.matched_via == "exact"
    assert result.rows[0].parsed.tag == "pl"
    # Mixed case in a REGION still normalizes: pl-PL reaches pl by fallback.
    assert negotiate_locale("pl-PL", SUPPORTED, DEFAULT_LOCALE).matched_via == (
        "region-fallback"
    )


def test_region_fallback_de_de_reaches_de() -> None:
    result = negotiate_locale("de-DE", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "de"
    assert result.matched_via == "region-fallback"
    # A script subtag in between still falls back to the primary language.
    assert negotiate_locale("de-Latn-DE", SUPPORTED, DEFAULT_LOCALE).selected == "de"
    # A subtag that is NOT a supported language matches nothing.
    assert negotiate_locale("xx-DE", SUPPORTED, DEFAULT_LOCALE).selected == "en"


def test_q_values_order_the_wishlist() -> None:
    header = "en;q=0.3, de;q=0.8, pl;q=0.5"
    result = negotiate_locale(header, SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "de"
    assert [row.parsed.tag for row in result.rows] == ["de", "pl", "en"]
    assert result.header == header


def test_equal_q_keeps_header_order() -> None:
    # de-DE and pl both q=1: the earlier element wins, deterministically.
    result = negotiate_locale("de-DE, pl", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "de"
    assert [row.parsed.tag for row in result.rows] == ["de-de", "pl"]
    flipped = negotiate_locale("pl, de-DE", SUPPORTED, DEFAULT_LOCALE)
    assert flipped.selected == "pl"


def test_duplicate_tags_are_both_parsed_first_wins() -> None:
    result = negotiate_locale("pl, pl", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "pl"
    assert len(result.rows) == 2


def test_q_zero_excludes_the_named_locale() -> None:
    result = negotiate_locale("pl;q=0, de", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "de"
    excluded = [row for row in result.rows if row.matched_via == "excluded"]
    assert [row.parsed.tag for row in excluded] == ["pl"]
    assert excluded[0].matched_locale == "pl"


def test_unknown_locales_fall_back_to_default_visibly() -> None:
    result = negotiate_locale("fr-CA,fr;q=0.9", SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "en"
    assert result.fell_back_to_default
    assert all(row.matched_via == "none" for row in result.rows)


def test_malformed_elements_are_skipped_not_fatal() -> None:
    header = "!!!, de-!!, 1nvalid, , de;q=2, pl;q=abc, en-"
    parsed = parse_accept_language(header)
    # "de;q=2" is a VALID range with an out-of-range q (lenient 1.0);
    # "pl;q=abc" is a valid range with junk q (lenient 1.0); everything
    # else — punctuation, a digit-leading tag, empties, a trailing dash —
    # is skipped, and nothing raises.
    assert [element.tag for element in parsed] == ["de", "pl"]
    assert all(element.quality == 1.0 for element in parsed)
    result = negotiate_locale(header, SUPPORTED, DEFAULT_LOCALE)
    assert result.selected == "de"


def test_q_precision_three_decimals_and_one_point_zero_zero_zero() -> None:
    parsed = parse_accept_language("de;q=0.250, en;q=1.000")
    assert [element.quality for element in parsed] == [0.25, 1.0]


def test_whitespace_around_elements_and_parameters_is_tolerated() -> None:
    parsed = parse_accept_language(" de ; q=0.5 , en ")
    assert [(element.tag, element.quality) for element in parsed] == [("de", 0.5), ("en", 1.0)]


# ── catalog: the fallback chain ─────────────────────────────────────────────


@pytest.fixture
def catalog() -> MessageCatalog:
    return MessageCatalog()


def test_catalog_discovers_and_compiles_real_po_files(catalog: MessageCatalog) -> None:
    assert catalog.tags() == ("de", "pl")
    assert catalog.locales() == ("en", "de", "pl")
    # The compiled bytes are real GNU .mo format: magic 0x950412de, little-endian.
    from guide.domain.i18n.catalog import LOCALES_DIR

    mo = compile_mo_bytes(LOCALES_DIR / "pl" / "LC_MESSAGES" / "messages.po", "pl")
    assert mo[:4] == b"\xde\x12\x04\x95"


def test_full_chain_de_de_to_de_to_default(catalog: MessageCatalog) -> None:
    assert catalog.translate("de-DE", "Upload a file") == "Datei hochladen"
    assert catalog.translate("de", "Upload a file") == "Datei hochladen"
    assert catalog.translate("de-AT", "Delete") == "Löschen"
    assert catalog.translate("pl-PL", "Delete") == "Usuń"


def test_unknown_locale_serves_the_source_string(catalog: MessageCatalog) -> None:
    assert catalog.translate("fr", "Upload a file") == "Upload a file"
    assert catalog.translate("zh-Hans-CN", "Cancel") == "Cancel"


def test_untranslated_message_falls_back_to_the_msgid(catalog: MessageCatalog) -> None:
    # The one deliberately untranslated German message serves its msgid.
    assert catalog.translate("de", "Language") == "Language"
    assert catalog.translate("pl", "Language") == "Język"


def test_missing_msgid_serves_itself(catalog: MessageCatalog) -> None:
    assert catalog.translate("de", "a key that was never extracted") == (
        "a key that was never extracted"
    )


def test_plural_sentences_per_locale_through_ngettext(catalog: MessageCatalog) -> None:
    assert catalog.plural_sentence("en", 1) == "1 file uploaded"
    assert catalog.plural_sentence("en", 0) == "0 files uploaded"
    assert catalog.plural_sentence("de", 1) == "1 Datei wurde hochgeladen"
    assert catalog.plural_sentence("de", 2) == "2 Dateien wurden hochgeladen"
    # Polish: three real forms driven by the catalog's Plural-Forms header.
    assert catalog.plural_sentence("pl", 1) == "1 plik został wysłany"
    assert catalog.plural_sentence("pl", 2) == "2 pliki zostały wysłane"
    assert catalog.plural_sentence("pl", 5) == "5 plików zostało wysłanych"
    assert catalog.plural_sentence("pl", 22) == "22 pliki zostały wysłane"
    assert catalog.plural_sentence("pl", 0) == "0 plików zostało wysłanych"


def test_catalog_entries_flag_the_untranslated_message(catalog: MessageCatalog) -> None:
    entries = {entry.msgid: entry for entry in catalog.entries()}
    assert entries["Language"].translations == (
        ("de", "Language", False),
        ("pl", "Język", True),
    )
    assert entries["Upload a file"].fully_translated


def test_no_catalogs_at_all_still_serves_the_source_strings(tmp_path: Path) -> None:
    empty = MessageCatalog(locales_dir=tmp_path)
    assert empty.tags() == ()
    assert empty.locales() == ("en",)
    assert empty.translate("de", "Upload a file") == "Upload a file"
    assert empty.plural_sentence("pl", 2) == "2 files uploaded"


# ── formatting: CLDR truth, pinned ──────────────────────────────────────────


def test_number_grouping_and_separators_per_locale() -> None:
    assert format_number(1234567.89, "en") == "1,234,567.89"
    assert format_number(1234567.89, "de") == "1.234.567,89"
    assert format_number(1234567.89, "pl") == "1 234 567,89"


def test_currency_placement_per_locale() -> None:
    assert format_currency(1234.5, "EUR", "en") == "€1,234.50"
    assert format_currency(1234.5, "EUR", "de") == "1.234,50 €"
    assert format_currency(1234.5, "EUR", "pl") == "1 234,50 €"


def test_datetime_labels_per_locale() -> None:
    assert format_instant(DEMO_INSTANT, "en") == "Mar 8, 2026, 7:30:00 AM"
    assert format_instant(DEMO_INSTANT, "de") == "08.03.2026, 07:30:00"
    assert format_instant(DEMO_INSTANT, "pl") == "8 mar 2026, 07:30:00"


def test_plural_category_math_against_cldr_truth() -> None:
    # Polish: one/few/many — the "few" rule reads the LAST digits, so 22
    # groups with 2 while 5 and 0 are "many". Fractions fall to "other".
    assert [plural_category("pl", n) for n in (0, 1, 2, 5, 22)] == [
        "many",
        "one",
        "few",
        "many",
        "few",
    ]
    assert plural_category("pl", 11) == "many"  # the 11-14 exception
    assert plural_category("pl", 1.5) == "other"
    # English and German distinguish only one/other.
    assert [plural_category("en", n) for n in (0, 1, 2)] == ["other", "one", "other"]
    assert [plural_category("de", n) for n in (0, 1, 2)] == ["other", "one", "other"]


def test_plural_categories_describe_the_grammar() -> None:
    assert plural_categories("en") == ("one", "other")
    assert plural_categories("de") == ("one", "other")
    assert plural_categories("pl") == ("one", "few", "many", "other")


def test_ngettext_and_cldr_categories_agree_on_integers(
    catalog: MessageCatalog,
) -> None:
    # The catalog's three-form header and babel's CLDR categories land on
    # the same form for every integer count the demo shows.
    for count in (0, 1, 2, 5, 22):
        category = plural_category("pl", count)
        expected = {"one": "został", "few": "zostały", "many": "zostało"}[category]
        assert expected in catalog.plural_sentence("pl", count)


# ── timezones: the wall-clock half ─────────────────────────────────────────


def test_wall_clock_across_zones_for_the_fixed_instant() -> None:
    utc_wall, utc_offset, utc_abbr = wall_clock(DEMO_INSTANT, "UTC")
    assert (utc_wall.isoformat(), utc_offset, utc_abbr) == (
        "2026-03-08T07:30:00+00:00",
        "+00:00",
        "UTC",
    )
    # New York sprang forward at 07:00 UTC: this instant is EDT, not EST.
    ny_wall, ny_offset, ny_abbr = wall_clock(DEMO_INSTANT, "America/New_York")
    assert (ny_wall.isoformat(), ny_offset, ny_abbr) == (
        "2026-03-08T03:30:00-04:00",
        "-04:00",
        "EDT",
    )
    # Kolkata: a half-hour offset zone, no DST.
    in_wall, in_offset, in_abbr = wall_clock(DEMO_INSTANT, "Asia/Kolkata")
    assert (in_wall.isoformat(), in_offset, in_abbr) == (
        "2026-03-08T13:00:00+05:30",
        "+05:30",
        "IST",
    )


def test_dst_boundary_is_decided_by_the_zone_not_the_math() -> None:
    before = datetime(2026, 3, 8, 6, 30, tzinfo=UTC)
    after = datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
    assert wall_clock(before, "America/New_York")[2] == "EST"  # 01:30 standard
    assert wall_clock(after, "America/New_York")[2] == "EDT"  # 03:30 daylight


def test_naive_instants_are_refused() -> None:
    with pytest.raises(ValueError, match="aware"):
        wall_clock(datetime(2026, 3, 8, 7, 30), "UTC")


def test_unknown_zone_names_raise_a_typed_error() -> None:
    with pytest.raises(UnknownZoneError):
        wall_clock(DEMO_INSTANT, "Mars/Olympus_Mons")


def test_render_wall_clock_crosses_both_axes() -> None:
    # The same instant+zone, labeled by two different locales.
    assert render_wall_clock(DEMO_INSTANT, "America/New_York", "en") == (
        "Mar 8, 2026, 3:30:00 AM"
    )
    assert render_wall_clock(DEMO_INSTANT, "America/New_York", "pl") == (
        "8 mar 2026, 03:30:00"
    )


def test_utc_offset_text_formats_half_hours() -> None:
    local = wall_clock(DEMO_INSTANT, "Asia/Kolkata")[0]
    assert utc_offset_text(local) == "+05:30"
    assert utc_offset_text(wall_clock(DEMO_INSTANT, "UTC")[0]) == "+00:00"


# ── the composite service ──────────────────────────────────────────────────


def test_service_renders_every_layer_in_one_locale() -> None:
    service = I18nService(MessageCatalog())
    rendering = service.render("de")
    assert rendering.locale == "de"
    assert ("Upload a file", "Datei hochladen") in rendering.ui_strings
    assert rendering.formatting.number == "1.234.567,89"
    assert rendering.plurals[1].sentence == "1 Datei wurde hochgeladen"
    assert rendering.zones[1].abbreviation == "EDT"


def test_service_negotiation_uses_the_servable_set() -> None:
    service = I18nService(MessageCatalog())
    assert service.supported_locales() == ("en", "de", "pl")
    assert service.negotiate("pl-PL,pl;q=0.8,en;q=0.3").selected == "pl"
