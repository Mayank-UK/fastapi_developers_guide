"""The message catalog: stdlib gettext over the repo's real .po files.

The catalogs under ``locales/<tag>/LC_MESSAGES/messages.po`` are REAL
gettext files — hand-written (demo scope) with proper headers and UTF-8
charsets — and the module compiles each one to GNU ``.mo`` format at
import with babel (``read_po`` → ``write_mo``), deterministic by
construction: same .po bytes in, same .mo bytes out, so nothing binary is
committed and nothing runtime-random can differ between boots. The
compiled bytes then feed stdlib ``gettext.GNUTranslations``, which is the
SERVING engine — including its ``Plural-Forms`` evaluation for
``ngettext`` (the per-locale plural expression rides in the .mo header,
exactly as gettext has worked since the nineties).

Msgids are the English SOURCE strings — classic gettext — so the default
locale needs no catalog of its own: the source language IS the fallback
floor. The fallback chain walks ``full tag → primary subtag → default``:
``de-DE`` finds ``de``'s catalog, ``fr`` finds no catalog and serves the
msgid, and an untranslated MESSAGE (empty ``msgstr``, kept deliberately
for one German key) serves the msgid too — a partially translated locale
degrades per message, never per page.
"""

import gettext
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

DEFAULT_LOCALE: Final[str] = "en"
"""The source language and the answer of last resort: msgids ARE English."""

LOCALES_DIR: Final[Path] = Path(__file__).resolve().parent / "locales"
"""The classic gettext tree: ``<tag>/LC_MESSAGES/messages.po``."""

CATALOG_DOMAIN: Final[str] = "messages"
"""The gettext domain this app's catalogs live under."""

UI_MESSAGES: Final[tuple[str, ...]] = (
    "Welcome to the FastAPI developers guide",
    "Upload a file",
    "Download",
    "Search the guide",
    "Save changes",
    "Cancel",
    "Delete",
    "Loading…",
    "Nothing here to see",
    "Language",
)
"""The demo UI's messages — the one-message-one-key discipline, applied."""

PLURAL_MSGID: Final[str] = "%d file uploaded"
PLURAL_MSGID_PLURAL: Final[str] = "%d files uploaded"
"""The plural message pair: one msgid family, per-locale plural forms."""


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One message's state across every catalog locale, for the panel."""

    msgid: str
    translations: tuple[tuple[str, str, bool], ...]
    """(locale tag, served string, translated-here) per catalog locale."""

    @property
    def fully_translated(self) -> bool:
        """False when any catalog locale falls back for this message."""
        return all(translated for _, _, translated in self.translations)


def compile_mo_bytes(po_path: Path, locale_tag: str) -> bytes:
    """Compile one .po file to GNU .mo bytes with babel, deterministically.

    The output is real compiled-catalog bytes — magic number, hash tables,
    plural header — produced in memory; nothing is written to disk and the
    same .po always compiles to the same .mo (babel's writer is a pure
    serializer, which is exactly why compiling at import needs no cache
    invalidation story).
    """
    with po_path.open("rb") as po_file:
        catalog = read_po(po_file, locale=locale_tag)
    buffer = io.BytesIO()
    write_mo(buffer, catalog)
    return buffer.getvalue()


class MessageCatalog:
    """Serves messages from the compiled catalogs, with the fallback chain."""

    def __init__(self, locales_dir: Path = LOCALES_DIR) -> None:
        """Compile every catalog under the tree once, at construction."""
        self._serving: dict[str, gettext.NullTranslations] = {}
        pattern = f"*/LC_MESSAGES/{CATALOG_DOMAIN}.po"
        for po_path in sorted(locales_dir.glob(pattern)):
            tag = po_path.relative_to(locales_dir).parts[0]
            self._serving[tag] = gettext.GNUTranslations(
                io.BytesIO(compile_mo_bytes(po_path, tag))
            )
        self._identity = gettext.NullTranslations()

    def tags(self) -> tuple[str, ...]:
        """The catalog locales that exist (the default needs no catalog)."""
        return tuple(sorted(self._serving))

    def locales(self) -> tuple[str, ...]:
        """Every servable locale: the default first, then catalog locales."""
        return (DEFAULT_LOCALE, *self.tags())

    def translate(self, locale: str, msgid: str) -> str:
        """One message in one locale, walking the fallback chain.

        ``de-DE`` → ``de`` → default; a locale with no catalog anywhere in
        the chain, and a message with no (or empty) translation, both serve
        the msgid — the source string is always the floor.
        """
        return self._translations_for(locale).gettext(msgid)

    def plural_sentence(self, locale: str, count: int) -> str:
        """The pluralized sentence for a count, via the catalog's own rules.

        ``ngettext`` picks the form using the ``Plural-Forms`` expression
        compiled into the locale's .mo (German two forms, Polish three);
        the default locale's identity carries gettext's built-in ``n != 1``
        rule. The count is interpolated into the chosen form.
        """
        return self._translations_for(locale).ngettext(
            PLURAL_MSGID, PLURAL_MSGID_PLURAL, count
        ) % count

    def entries(self) -> tuple[CatalogEntry, ...]:
        """Every UI message's per-locale state, for the panel's catalog view."""
        return tuple(
            CatalogEntry(
                msgid=msgid,
                translations=tuple(
                    (tag, self.translate(tag, msgid), self.translate(tag, msgid) != msgid)
                    for tag in self.tags()
                ),
            )
            for msgid in UI_MESSAGES
        )

    def _translations_for(self, locale: str) -> gettext.NullTranslations:
        """The serving translations for a locale after the fallback chain."""
        normalized = locale.lower()
        for candidate in (normalized, normalized.split("-", 1)[0]):
            translations = self._serving.get(candidate)
            if translations is not None:
                return translations
        return self._identity
