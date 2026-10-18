"""Locale formatting: CLDR data through babel, pure and deterministic.

Languages differ in far more than vocabulary: German writes ``1.234.567,89``
where English writes ``1,234,567.89``; a euro is ``€1,234.50`` in Dublin
and ``1.234,50 €`` in Berlin; dates order their parts and name their
months differently. None of that belongs in hand-rolled ``f-string`` code —
it is COUNTRY-LOCALE DATA, and the Unicode Common Locale Data Repository
(CLDR) is its canonical source. Babel is the Python engine over that
data, and this module is the repo's thin, typed surface over babel:
numbers, currency, dates, and the CLDR plural CATEGORIES (``one``, few,
many, other — the labels grammar, not the words).

Determinism is the contract: every function here is pure in its inputs —
the same value, locale tag, and instant always produce the same string —
so tests pin exact output and the demo panel can show real formatting
without any clock or ambient locale leaking in. Locale tags are BCP 47
hyphenated (``de-DE``) and normalized to babel's underscore form at the
one seam where it matters.
"""

from datetime import datetime
from typing import Final

from babel import Locale
from babel.dates import format_datetime
from babel.numbers import format_currency as babel_currency
from babel.numbers import format_decimal as babel_decimal

CLDR_CATEGORY_ORDER: Final[tuple[str, ...]] = (
    "zero",
    "one",
    "two",
    "few",
    "many",
    "other",
)
"""Canonical CLDR cardinal-plural categories, in CLDR's own order."""


def locale_display(locale_tag: str) -> tuple[str, str]:
    """(english name, native name) for a tag, from CLDR locale data."""
    locale = babel_locale(locale_tag)
    return locale.english_name or locale_tag, locale.display_name or locale_tag


def plural_categories(locale_tag: str) -> tuple[str, ...]:
    """The CLDR plural categories a locale's grammar distinguishes.

    English and German distinguish ``one``/``other``; Polish distinguishes
    ``one``/``few``/``many``/``other`` — the grammar that makes ``5`` and
    ``22`` take DIFFERENT forms in Polish while ``1`` and ``21`` share one.
    """
    locale = babel_locale(locale_tag)
    rules = locale.plural_form.rules
    present = set(rules) | {"other"}  # "other" is always the catch-all
    return tuple(category for category in CLDR_CATEGORY_ORDER if category in present)


def plural_category(locale_tag: str, count: int | float) -> str:
    """The CLDR plural category a count falls into, for one locale.

    This is the category MATH — the truth source the demo trusts: Polish
    1 → one, 2 → few, 5 → many, 22 → few (not "many": the few-rule looks
    at the last digit, so 22 groups with 2), and fractions → other.
    """
    return str(babel_locale(locale_tag).plural_form(count))


def format_number(value: float, locale_tag: str) -> str:
    """A decimal number with the locale's grouping and decimal separators."""
    return babel_decimal(value, locale=babel_locale(locale_tag))


def format_currency(value: float, currency_code: str, locale_tag: str) -> str:
    """A money amount: the locale decides symbol placement and separators."""
    return babel_currency(value, currency_code, locale=babel_locale(locale_tag))


def format_instant(instant: datetime, locale_tag: str) -> str:
    """A datetime in the locale's medium format, in the instant's own zone.

    The instant carries its timezone (the caller passes UTC or a zoned
    wall time — see ``timezones.py`` for the two-axis model); babel
    renders labels and order, never the zone.
    """
    return format_datetime(instant, format="medium", locale=babel_locale(locale_tag))


def babel_locale(locale_tag: str) -> Locale:
    """Parse a BCP 47 hyphenated tag into babel's Locale.

    babel's parser is underscore-native (``de_DE``); the hyphen form the
    HTTP world speaks is normalized here, once, at the seam.
    """
    return Locale.parse(locale_tag.replace("-", "_"))
