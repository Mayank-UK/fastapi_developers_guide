"""Topic 27 — Internationalization (the language layer arrives).

The media group opened with bytes; this topic adds the fact that those
bytes serve a WORLD: the default API has no single country. It starts
from what "global by default" actually covers — negotiation, catalogs,
formatting, timezones — and what it doesn't; builds the RFC 9110
Accept-Language negotiation engine with the negotiator demo INLINE in
that section (one header, every layer it changes, live); teaches gettext
message catalogs as real files over the repo's own de/pl catalogs
(compiled to .mo at import, deterministically); formats numbers, currency,
and dates from CLDR data through babel and takes plural RULES seriously
(Polish's one/few/many is the exhibit); separates the two axes of time —
UTC instants versus wall clocks versus locale labels — over zoneinfo; and
closes with the translation workflow as a loop over this repo's own
catalogs, the one-message-one-key discipline, and what rots. Terminal
companion: a curl tour of Accept-Language variants.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="internationalization",
    title="Internationalization",
    subtitle=(
        "Global by default: Accept-Language negotiation per RFC 9110, gettext "
        "message catalogs as real files with fallback chains, CLDR formatting "
        "through babel, plural category math (Polish's one/few/many), timezones "
        "versus locales over zoneinfo, and the extract→translate→compile→ship "
        "workflow — one live negotiator that answers any header you send."
    ),
    group="media-realtime",
    order=27,
    sections=[
        # ── 1. Global by default ───────────────────────────────────────────
        Section(
            id="global-by-default",
            title="Global by default",
            blocks=[
                TextBlock(
                    kind="text",
                    id="global-pitch",
                    text=(
                        "Every API built so far in this guide answered in one "
                        "language, one number format, one clock — not because "
                        "anyone chose that, but because defaults are silent. "
                        "The moment an API is reachable from anywhere, it is an "
                        "international API whether its authors noticed or not: "
                        "a Berlin client sends ``Accept-Language: de-DE`` on "
                        "every request, a São Paulo client reads ``1.234.567,89`` "
                        "as one point two million (an English reader parses the "
                        "same digits as a comma error), and a Mumbai client "
                        "lives half an hour off every whole-hour timezone you "
                        "hardcode. Internationalization — i18n, the "
                        "eighteen-letter abbreviation the field actually uses — "
                        "is the discipline of making those differences DATA "
                        "instead of accidents: the code never branches on "
                        "country, it asks a small set of engines what the user's "
                        "context calls for."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="global-scope-pitch",
                    text=(
                        "Scoping matters, because \"internationalize\" is a word "
                        "that swallows four different problems, and each has its "
                        "own machinery in this stack. What this topic covers, "
                        "and what it deliberately leaves alone:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="global-scope",
                    ordered=True,
                    items=[
                        "Language negotiation — deciding WHICH locale to serve, "
                        "from the ``Accept-Language`` header every browser sends: "
                        "an HTTP problem with an RFC answer, built in section two.",
                        "Message catalogs — serving TRANSLATED strings from real "
                        "gettext files with a fallback chain, so a missing "
                        "translation degrades one message, never a whole page "
                        "(section three).",
                        "Formatting — numbers, currency, and dates rendered from "
                        "CLDR locale data, plus plural RULES that are category "
                        "math, not a singular/plural boolean (section four).",
                        "Timezones — the OTHER axis: UTC instants versus wall "
                        "clocks, composed with locale labels only at the edge "
                        "(section five).",
                        "Translation workflow — the extract→translate→compile→"
                        "ship loop that keeps catalogs alive as code changes "
                        "(section six).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="global-not-scope",
                    text=(
                        "What it leaves alone is content translation and "
                        "localization proper: translating the POSTS this guide's "
                        "users write is a content problem (each user-authored "
                        "row would carry its own translations), and "
                        "locale-specific business rules — which currency to "
                        "CHARGE in, which regions a feature ships to — are "
                        "product decisions, not formatting decisions. The line "
                        "worth holding: i18n machinery is generic and lives in "
                        "the platform layer this topic builds; what crosses it "
                        "is data about a request's locale, flowing through the "
                        "same ports-and-adapters seams every other cross-cutting "
                        "concern used. Note also what i18n does NOT buy for "
                        "free: text direction (an RTL layout like Arabic or "
                        "Hebrew needs UI mirroring, a frontend concern), and "
                        "translation QUALITY — the catalog only serves what "
                        "someone actually translated."
                    ),
                ),
            ],
        ),
        # ── 2. Accept-Language negotiation ─────────────────────────────────
        Section(
            id="accept-language-negotiation",
            title="Accept-Language negotiation",
            lead="This section carries the topic's demo — the i18n negotiator.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="negotiation-pitch",
                    text=(
                        "The negotiation input arrives before your handler "
                        "runs: every browser sends ``Accept-Language`` on every "
                        "request — Chrome in Germany sends ``de-DE,de;q=0.9,"
                        "en-US;q=0.8,en;q=0.7`` — and RFC 9110 §12.5.4 defines "
                        "what it means. The header is a comma-separated wishlist "
                        "of language ranges, each optionally weighted with a "
                        "quality value: ``q`` runs 0.000 to 1.000 (default 1), "
                        "lower means less preferred, and ``q=0`` means "
                        "explicitly unacceptable. Tags are BCP 47 ranges — "
                        "``de-DE`` is German as spoken in Germany — and they "
                        "are case-insensitive, so ``DE-de`` and ``de-DE`` are "
                        "the same range. One special range exists: ``*`` "
                        "matches anything not named. The header is a WISHLIST, "
                        "not a demand — the server holds the inventory of "
                        "locales it actually has, and negotiation is the "
                        "act of finding the best mutual answer."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="negotiation-rules-pitch",
                    text=(
                        "The engine this repo runs is one pure module, and its "
                        "decisions are exactly the ones the RFC leaves open, "
                        "made once and tested: candidates are considered in "
                        "descending q with header order breaking ties (the "
                        "deterministic ordering — no flapping between equal "
                        "wishes), each candidate matches by exact tag first and "
                        "then by primary subtag — ``de-DE`` and even "
                        "``de-Latn-DE`` reach a ``de`` catalog, the region "
                        "fallback — and a match an earlier ``q=0`` excluded is "
                        "honored. The core loop reads small enough to check by "
                        "eye against the panel:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="negotiation-engine-quote",
                    language="py",
                    caption="The negotiation loop: q order, wildcard, exact, then region fallback — first match wins.",
                    source="server/guide/domain/i18n/negotiation.py",
                    snippet=(
                        "    candidates = sorted(\n"
                        "        (element for element in elements if element.quality > 0.0),\n"
                        "        key=lambda element: (-element.quality, element.position),\n"
                        "    )\n"
                        "\n"
                        "    rows: list[NegotiationRow] = []\n"
                        "    selected: str | None = None\n"
                        "    selected_via: LanguageRange = \"default\"\n"
                        "    for element in candidates:\n"
                        "        if element.tag == \"*\":\n"
                        "            pick = next(\n"
                        "                (tag for tag in supported if tag.lower() not in excluded), None\n"
                        "            )\n"
                        "            if pick is not None and selected is None:\n"
                        "                selected, selected_via = pick, \"wildcard\"\n"
                        "            rows.append(\n"
                        "                NegotiationRow(\n"
                        "                    parsed=element, matched_locale=pick, matched_via=\"wildcard\"\n"
                        "                )\n"
                        "            )\n"
                        "            continue\n"
                        "        exact = _exact_match(element.tag, lowered)\n"
                        "        if exact is not None and exact not in excluded:\n"
                        "            if selected is None:\n"
                        "                selected, selected_via = exact, \"exact\"\n"
                        "            rows.append(\n"
                        "                NegotiationRow(parsed=element, matched_locale=exact, matched_via=\"exact\")\n"
                        "            )\n"
                        "            continue\n"
                        "        primary = element.tag.split(\"-\", 1)[0]\n"
                        "        regional = _exact_match(primary, lowered)\n"
                        "        if regional is not None and regional not in excluded:\n"
                        "            if selected is None:\n"
                        "                selected, selected_via = regional, \"region-fallback\"\n"
                        "            rows.append(\n"
                        "                NegotiationRow(\n"
                        "                    parsed=element, matched_locale=regional, matched_via=\"region-fallback\"\n"
                        "                )\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="negotiation-hostile-pitch",
                    text=(
                        "Hostile input policy, stated once because this is a "
                        "PREFERENCE header: a malformed element is skipped, "
                        "never an error. The parser validates each range "
                        "against the BCP 47 shape (an alphabetic primary "
                        "subtag, alphanumeric subsegs, or ``*``), reads the "
                        "first ``q`` parameter, and treats junk weights — "
                        "``q=2``, ``q=abc`` — as absent (q=1), because "
                        "unparseable metadata carries no information. The "
                        "result: no value a client can send makes negotiation "
                        "fail; the worst case is the DEFAULT locale, and the "
                        "result says so — ``fell_back_to_default`` — so the "
                        "fallback is visible, not silent. That is the same "
                        "lenient-edges stance this guide took for Range "
                        "headers, applied to the one header browsers send "
                        "whether you read it or not."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="negotiation-router-pitch",
                    text=(
                        "The router half is deliberately the smallest in the "
                        "guide: read the real header, negotiate, render "
                        "everything in the negotiated locale. FastAPI maps a "
                        "``Header()`` parameter to the wire name "
                        "automatically (underscores become hyphens), and "
                        "``None`` is the honest default — the absent header "
                        "is a normal case, not an error:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="negotiation-router-quote",
                    language="py",
                    caption="The whole router: one real header in, every layer answered in the negotiated locale.",
                    source="server/guide/presentation/routers/demo/i18n.py",
                    snippet=(
                        "@router.get(NEGOTIATE_ROUTE, response_model=NegotiatorRound)\n"
                        "async def read_negotiation(\n"
                        "    service: ServiceDep,\n"
                        "    accept_language: Annotated[str | None, Header()] = None,\n"
                        ") -> NegotiatorRound:\n"
                        "# …\n"
                        "    negotiation = service.negotiate(accept_language)\n"
                        "    rendering = service.render(negotiation.selected)\n"
                        "    return build_negotiator_round(service, negotiation, rendering)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="negotiation-demo-pitch",
                    text=(
                        "Try it: the negotiator panel sends any "
                        "``Accept-Language`` value you pick — presets or free "
                        "text — and answers with the FULL ranked parse: every "
                        "element's raw text, normalized tag, q, and how it "
                        "matched (exact, region-fallback, wildcard, none, or "
                        "excluded). Watch the locale change and everything "
                        "downstream change with it — the UI strings from the "
                        "real catalog (section three), the number/currency/"
                        "date formatting (section four), the plural sentences "
                        "with their CLDR categories, and the fixed instant on "
                        "three wall clocks labeled in the negotiated locale "
                        "(section five). Send ``fr-CA`` and see the visible "
                        "default fallback; send ``en;q=0, *`` and watch the "
                        "wildcard honor the exclusion; send garbage and watch "
                        "it be skipped, element by element."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="i18n:negotiator",
                    title="The i18n negotiator",
                    description=(
                        "GET /api/demo/i18n serves the panel (policy: default "
                        "locale en, servable en/de/pl with native names and "
                        "CLDR plural grammar; fixed instant 2026-03-08T07:30Z, "
                        "inputs 1234567.89 / EUR 1234.50 / counts 0,1,2,5,22; "
                        "the catalog table with the one deliberately "
                        "untranslated German message; endpoint tour; honesty "
                        "notes — hand-written demo-scope .po catalogs, "
                        "deterministic in-memory .mo compilation). GET "
                        "/api/demo/i18n/negotiate reads the REAL Accept-Language "
                        "header (presets and free input set it client-side): "
                        "header echo, selected locale, matched_via, "
                        "fell_back_to_default, the full ranked parse (raw, "
                        "tag, q, matched-via per element), UI strings via the "
                        "compiled catalogs, CLDR number/currency/date "
                        "formatting, plural rows (count → category + "
                        "ngettext sentence), and the fixed instant across "
                        "UTC / America/New_York / Asia/Kolkata with offsets, "
                        "abbreviations, and locale-labeled wall clocks."
                    ),
                ),
            ],
        ),
        # ── 3. gettext and catalogs ────────────────────────────────────────
        Section(
            id="gettext-and-catalogs",
            title="gettext and message catalogs",
            blocks=[
                TextBlock(
                    kind="text",
                    id="gettext-pitch",
                    text=(
                        "Translated strings need a HOME that code reviews, "
                        "diffs, and tooling can see — and the industry answer "
                        "is older than the web: gettext, the GNU translation "
                        "stack. The unit is the MESSAGE CATALOG: your source "
                        "strings are the keys (the msgid IS the English "
                        "sentence — classic gettext, which is why the default "
                        "locale needs no catalog at all), translations live "
                        "one file per locale in a ``<locale>/LC_MESSAGES`` "
                        "tree, and the files are plain text ``.po`` that "
                        "compiles to binary ``.mo`` for serving. The lifetime "
                        "is the loop: mark strings for extraction, extract "
                        "them into catalogs, translators fill the msgstr "
                        "fields, compile, ship. This repo carries two real "
                        "catalogs — German and Polish, chosen deliberately: "
                        "German because ``de-DE``/``de-AT`` make the region "
                        "fallback concrete, Polish because its plural grammar "
                        "is the richest thing in section four — and compiles "
                        "them at import, deterministically:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="gettext-compile-quote",
                    language="py",
                    caption="Real .po bytes in, real .mo bytes out — same input, same output, nothing binary committed.",
                    source="server/guide/domain/i18n/catalog.py",
                    snippet=(
                        "def compile_mo_bytes(po_path: Path, locale_tag: str) -> bytes:\n"
                        "# …\n"
                        "    with po_path.open(\"rb\") as po_file:\n"
                        "        catalog = read_po(po_file, locale=locale_tag)\n"
                        "    buffer = io.BytesIO()\n"
                        "    write_mo(buffer, catalog)\n"
                        "    return buffer.getvalue()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="gettext-po-pitch",
                    text=(
                        "The Polish catalog is quotable because it IS the "
                        "artifact — headers declare the charset and the plural "
                        "expression (three forms: one for 1, few for 2-4 "
                        "except 12-14, many for the rest), and the messages "
                        "are pairs a translator can fill without touching "
                        "code. Note the plural entry: ONE msgid family with "
                        "one msgstr per form the grammar requires:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="gettext-po-quote",
                    language="po",
                    caption="The repo's real Polish catalog: headers, charset, the plural expression, and translated pairs.",
                    source="server/guide/domain/i18n/locales/pl/LC_MESSAGES/messages.po",
                    snippet=(
                        "msgid \"\"\n"
                        "msgstr \"\"\n"
                        "\"Project-Id-Version: fastapi-developers-guide 1.0\\n\"\n"
                        "\"Language: pl\\n\"\n"
                        "\"MIME-Version: 1.0\\n\"\n"
                        "\"Content-Type: text/plain; charset=UTF-8\\n\"\n"
                        "\"Content-Transfer-Encoding: 8bit\\n\"\n"
                        "\"Plural-Forms: nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\\n\"\n"
                        "\n"
                        "# …\n"
                        "msgid \"%d file uploaded\"\n"
                        "msgid_plural \"%d files uploaded\"\n"
                        "msgstr[0] \"%d plik został wysłany\"\n"
                        "msgstr[1] \"%d pliki zostały wysłane\"\n"
                        "msgstr[2] \"%d plików zostało wysłanych\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="gettext-fallback-pitch",
                    text=(
                        "Serving is stdlib ``gettext.GNUTranslations`` over the "
                        "compiled bytes — including its ``ngettext``, which "
                        "evaluates the catalog's own plural expression per "
                        "count. Around it sits the FALLBACK CHAIN, the part "
                        "most homegrown i18n gets wrong: a locale request "
                        "walks the full tag, then the primary subtag, then the "
                        "default — ``de-DE`` finds ``de``'s catalog, ``fr`` "
                        "finds no catalog and serves the msgid, and an "
                        "untranslated MESSAGE (empty msgstr — one German key "
                        "is deliberately left so, visible on the panel) also "
                        "serves the msgid. The floor is the source string, "
                        "reached per message, never per page:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="gettext-chain-quote",
                    language="py",
                    caption="The fallback chain: full tag → primary subtag → identity (the msgid itself).",
                    source="server/guide/domain/i18n/catalog.py",
                    snippet=(
                        "    def _translations_for(self, locale: str) -> gettext.NullTranslations:\n"
                        "# …\n"
                        "        normalized = locale.lower()\n"
                        "        for candidate in (normalized, normalized.split(\"-\", 1)[0]):\n"
                        "            translations = self._serving.get(candidate)\n"
                        "            if translations is not None:\n"
                        "                return translations\n"
                        "        return self._identity"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="gettext-coda",
                    text=(
                        "Why gettext over the younger alternatives — message "
                        "keys in code with JSON dictionaries, or a "
                        "translation SaaS — is worth saying out loud. The "
                        "file format is thirty years stable and every "
                        "translation tool speaks it; the extraction tooling "
                        "reads SOURCE and finds strings to translate without "
                        "hand-maintained key lists; the fallback semantics "
                        "are defined, tested, and boring; and the whole "
                        "thing diffs and merges in pull requests like code. "
                        "A JSON dict gives you lookup and nothing else — no "
                        "plural grammar, no extraction, no tooling — and "
                        "keys like ``menu.item.3`` rot silently because "
                        "nothing connects them to the code that needs them. "
                        "The cost you accept: the compile step, which this "
                        "repo folds into import so a stale ``.mo`` can never "
                        "ship."
                    ),
                ),
            ],
        ),
        # ── 4. Formatting and plurals ──────────────────────────────────────
        Section(
            id="formatting-and-plurals",
            title="Formatting and plural rules",
            blocks=[
                TextBlock(
                    kind="text",
                    id="formatting-pitch",
                    text=(
                        "Translation covers WORDS; formatting covers "
                        "everything else a locale decides, and hand-rolling "
                        "it is how APIs ship bugs that look like features. "
                        "The same number, 1234567.89, is ``1,234,567.89`` in "
                        "English, ``1.234.567,89`` in German, and "
                        "``1 234 567,89`` in Polish — grouping and decimal "
                        "characters are locale data, not taste. Currency "
                        "adds placement: the same euro is ``€1,234.50`` in "
                        "an English locale and ``1.234,50 €`` in a German "
                        "one (and CURRENCY CHOICE stays a product decision "
                        "— formatting a euro is not deciding to charge "
                        "euros). Dates reorder wholesale: the same instant "
                        "labels itself ``Mar 8, 2026, 7:30 AM``, "
                        "``08.03.2026, 07:30``, and ``8 mar 2026, 07:30``. "
                        "The canonical source for all of it is CLDR — the "
                        "Unicode Common Locale Data Repository — and babel "
                        "is its Python engine; this repo's formatting "
                        "service is a thin typed surface over it, pure in "
                        "its inputs so every string is deterministic and "
                        "testable."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="plurals-pitch",
                    text=(
                        "Plurals are where formatting stops being cosmetic "
                        "and starts being GRAMMAR, because \"singular or "
                        "plural\" is an English-shaped assumption. CLDR "
                        "defines plural CATEGORIES — zero, one, two, few, "
                        "many, other — and each locale's grammar maps "
                        "counts to categories by RULES, not by n==1. Polish "
                        "is the exhibit this repo ships: it distinguishes "
                        "one, few, many, and other, and the math reads the "
                        "LAST DIGITS — 1 is one, but so is 21 and 31; 2-4 "
                        "are few, EXCEPT 12-14; 0, 5-21, and 11-14 are "
                        "many. So \"5 files\" and \"22 files\" take "
                        "DIFFERENT forms in Polish, and any code that "
                        "branches on ``n != 1`` produces a sentence no "
                        "Polish speaker would write. The category math "
                        "lives in one function, babel's CLDR rules behind "
                        "it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="plurals-quote",
                    language="py",
                    caption="The category math: babel's CLDR rules are the truth source, one typed seam.",
                    source="server/guide/domain/i18n/formatting.py",
                    snippet=(
                        "def plural_category(locale_tag: str, count: int | float) -> str:\n"
                        "# …\n"
                        "    return str(babel_locale(locale_tag).plural_form(count))\n"
                        "# …\n"
                        "def format_currency(value: float, currency_code: str, locale_tag: str) -> str:\n"
                        "# …\n"
                        "    return babel_currency(value, currency_code, locale=babel_locale(locale_tag))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="plurals-two-engines-pitch",
                    text=(
                        "Two truth sources meet in the plural demo, and "
                        "their agreement is pinned by test rather than "
                        "assumed. The SENTENCE comes from gettext's "
                        "``ngettext`` evaluating the catalog's own "
                        "``Plural-Forms`` header — three forms for Polish, "
                        "chosen because that is babel's own expression for "
                        "the locale. The CATEGORY LABEL comes from babel's "
                        "CLDR rules, which know a fourth form (``other``) "
                        "that fires only on fractions like 1.5 — a count "
                        "integer never reaches, which is exactly why the "
                        "three-form gettext header and the four-category "
                        "CLDR grammar agree on every integer. The demo's "
                        "counts make the grammar impossible to miss: 0 → "
                        "many, 1 → one, 2 → few, 5 → many, 22 → few — "
                        "watch \"5 plików zostało wysłanych\" and \"22 "
                        "pliki zostały wysłane\" differ in the negotiator "
                        "while English renders both through plain "
                        "\"files\"."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="formatting-coda",
                    text=(
                        "The engineering discipline that keeps this honest "
                        "is DETERMINISM: the formatting service never reads "
                        "a clock, an environment locale, or a machine "
                        "timezone — every input is a parameter or a pinned "
                        "constant, so tests assert exact strings (nbsp "
                        "grouping separators included) and the panel's "
                        "output is reproducible to the byte. That is also "
                        "the portable rule for your own endpoints: never "
                        "let ``str()`` or f-strings format user-facing "
                        "numbers and dates directly — pass values through "
                        "the locale-aware formatters at the edge, exactly "
                        "as this repo does, and keep the domain's internal "
                        "representations unformatted (a float, an aware "
                        "datetime) until the moment of display."
                    ),
                ),
            ],
        ),
        # ── 5. Timezones versus locales ────────────────────────────────────
        Section(
            id="timezones-versus-locales",
            title="Timezones versus locales",
            blocks=[
                TextBlock(
                    kind="text",
                    id="zones-two-axis-pitch",
                    text=(
                        "Time and language are two axes that meet only at "
                        "the edge, and conflating them is the classic bug "
                        "(\"the German format shows New York time\"). The "
                        "model to hold: an INSTANT is a moment on the "
                        "world clock — UTC is its coordinate system; a "
                        "ZONE is a wall clock a place agrees to read that "
                        "instant on (with DST jumps and half-hour offsets "
                        "encoded in the IANA rules); a LOCALE is how any "
                        "wall time gets LABELED — month names, ordering, "
                        "12/24 hour. German does not imply Berlin's clock, "
                        "and UTC storage does not imply American-formatted "
                        "output; the negotiator renders the SAME instant "
                        "on three walls in whatever locale negotiated. "
                        "The wall-clock half is stdlib ``zoneinfo``:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="zones-quote",
                    language="py",
                    caption="One instant, one wall: zoneinfo decides the reading; the locale only labels it.",
                    source="server/guide/domain/i18n/timezones.py",
                    snippet=(
                        "def wall_clock(instant: datetime, zone_name: str) -> tuple[datetime, str, str]:\n"
                        "# …\n"
                        "    if instant.tzinfo is None:\n"
                        "        raise ValueError(\"wall_clock needs an aware instant — store and pass UTC\")\n"
                        "    local = instant.astimezone(zone(zone_name))\n"
                        "    return local, utc_offset_text(local), local.tzname() or zone_name\n"
                        "# …\n"
                        "def render_wall_clock(instant: datetime, zone_name: str, locale_tag: str) -> str:\n"
                        "# …\n"
                        "    return format_instant(instant.astimezone(zone(zone_name)), locale_tag)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="zones-demo-pitch",
                    text=(
                        "The demo's fixed instant is chosen to make the "
                        "rules visible: 2026-03-08 07:30 UTC is ninety "
                        "minutes after New York's spring-forward jump "
                        "(02:00 EST → 03:00 EDT, which swallows an hour), "
                        "so the panel shows ``03:30 EDT`` with offset "
                        "``-04:00`` — an hour that simply does not exist "
                        "on that wall — beside ``07:30 UTC`` and "
                        "``13:00 IST``, Kolkata's half-hour-offset zone "
                        "(``+05:30``, no DST, the case that breaks every "
                        "hardcoded whole-hour offset). DST is decided by "
                        "the zone's own data at the instant in question "
                        "(06:30 UTC the same morning is still ``EST``), "
                        "never by arithmetic in your code — and a NAIVE "
                        "datetime is refused loudly, because \"7:30 with "
                        "no zone\" is not a moment anyone can render."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="zones-storage-pitch",
                    text=(
                        "The storage discipline follows from the model, "
                        "and it is the part production code gets wrong "
                        "for years before anyone feels it: store and "
                        "communicate instants in UTC (this guide's "
                        "timestamps have been ISO-8601 UTC since its "
                        "first endpoint), convert to a wall clock only "
                        "at the display edge, and let the ZONE come from "
                        "the user's profile or header — never from the "
                        "server's machine timezone. The failure modes all "
                        "come from breaking one rule: naive datetimes "
                        "arithmetic-shift on storage (UTC \"fixes\" "
                        "silently); future events stored as wall time "
                        "break when a legislature moves a DST boundary "
                        "(an instant is a rule, a wall time is a "
                        "snapshot); and per-server local times make a "
                        "fleet disagree about \"now\". zoneinfo ships "
                        "with the IANA database as its authority — "
                        "updated by the platform, not by your release "
                        "calendar — and unknown zone names raise a typed "
                        "error rather than guessing a clock."
                    ),
                ),
            ],
        ),
        # ── 6. The translation workflow ────────────────────────────────────
        Section(
            id="translation-workflow",
            title="The translation workflow",
            blocks=[
                TextBlock(
                    kind="text",
                    id="workflow-pitch",
                    text=(
                        "Catalogs rot unless changing code mechanically "
                        "updates them, so the workflow is a LOOP, not a "
                        "one-time setup. Extract: a scanner (pybabel "
                        "extract, or xgettext) walks the source, finds "
                        "marked strings, and writes a POT template — the "
                        "msgids that exist TODAY. Translate: the template "
                        "merges into each locale's ``.po`` (new messages "
                        "arrive untranslated, deleted ones leave \"obsolete\" "
                        "comments), and a translator — a person with a "
                        "translation tool, not a developer with a text "
                        "editor, though the files are plain enough for "
                        "both — fills the msgstr fields. Compile: ``.po`` "
                        "to ``.mo`` (msgfmt, or babel's in-memory writer "
                        "as here). Ship: the compiled catalogs ride the "
                        "deploy, and the running process serves them. "
                        "This repo folds compile into import precisely so "
                        "step four cannot ship a stale binary."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="workflow-discipline-pitch",
                    text=(
                        "The discipline that keeps the loop cheap is "
                        "ONE MESSAGE, ONE KEY: each user-visible sentence "
                        "is one msgid, complete and self-contained, "
                        "marked at the point of use. The rules fall out "
                        "of how translators work:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="workflow-discipline",
                    ordered=False,
                    items=[
                        "Whole sentences — never words to concatenate "
                        "afterward; grammar reorders clauses per language, "
                        "so \"Upload\" + noun assembly cannot be translated.",
                        "Interpolation, not splicing — placeholders like "
                        "``%d`` ride INSIDE the msgid (\"%d file "
                        "uploaded\") so translators position the number "
                        "where their grammar wants it.",
                        "Context over cleverness — two uses of \"Open\" "
                        "(verb versus adjective) are two messages; a "
                        "translator cannot see your code, only your string.",
                        "Untranslated is a state, not a failure — an empty "
                        "msgstr serves the source string (this repo keeps "
                        "one German message empty ON PURPOSE to show it), "
                        "so partial translations ship safely and the "
                        "extraction report shows what's missing.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="workflow-keys-quote-pitch",
                    text=(
                        "The message set this topic ships is exactly that "
                        "discipline, real and small enough to read whole — "
                        "each string a complete sentence, placeholders "
                        "inside, no composition expected of callers:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="workflow-keys-quote",
                    language="py",
                    caption="The message set: whole sentences as msgids — the one-message-one-key discipline applied.",
                    source="server/guide/domain/i18n/catalog.py",
                    snippet=(
                        "UI_MESSAGES: Final[tuple[str, ...]] = (\n"
                        "    \"Welcome to the FastAPI developers guide\",\n"
                        "    \"Upload a file\",\n"
                        "    \"Download\",\n"
                        "    \"Search the guide\",\n"
                        "    \"Save changes\",\n"
                        "    \"Cancel\",\n"
                        "    \"Delete\",\n"
                        "    \"Loading…\",\n"
                        "    \"Nothing here to see\",\n"
                        "    \"Language\",\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="workflow-rot-pitch",
                    text=(
                        "What rots is specific, and worth naming so a code "
                        "review can catch it. Hardcoded strings creep in "
                        "outside the message set — an error message typed "
                        "straight into a handler, a label on a new "
                        "endpoint — invisible to extraction, untranslatable "
                        "forever. Concatenated sentences break grammar "
                        "silently (\"You have \" + n + \" files\" reads as "
                        "gibberish the moment a locale reorders it). "
                        "Untranslated keys accumulate quietly, which is "
                        "why the catalog panel shows per-locale coverage "
                        "and why this repo marks its one deliberate gap "
                        "explicitly — the German \"Language\" message "
                        "serves its msgid, on purpose, visibly:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="workflow-de-quote",
                    language="po",
                    caption="The German catalog's tail: the deliberate untranslated message beside the plural pair.",
                    source="server/guide/domain/i18n/locales/de/LC_MESSAGES/messages.po",
                    snippet=(
                        "msgid \"Language\"\n"
                        "msgstr \"\"\n"
                        "\n"
                        "msgid \"%d file uploaded\"\n"
                        "msgid_plural \"%d files uploaded\"\n"
                        "msgstr[0] \"%d Datei wurde hochgeladen\"\n"
                        "msgstr[1] \"%d Dateien wurden hochgeladen\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="workflow-coda",
                    text=(
                        "Run the loop against THIS repo to make it "
                        "concrete: add a message to ``UI_MESSAGES``, and "
                        "the next negotiation round serves the English "
                        "msgid for every locale — the safe default. Add "
                        "the msgstr to the German ``.po``, and German "
                        "rounds pick it up with no other change; the "
                        "compile already happened at import. That is the "
                        "whole contract between code and translators: "
                        "developers owe complete, marked, stable messages; "
                        "translators owe filled msgstrs; the machinery "
                        "guarantees that any gap degrades to the source "
                        "language instead of an error, and the panel "
                        "makes the current state of that contract visible "
                        "at a glance."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — headers in, negotiated worlds out.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Five stops, all against the negotiate endpoint "
                        "with real headers: no header at all (the visible "
                        "default fallback), the German region fallback "
                        "with translated strings and reformatted numbers, "
                        "Polish plural category math, the wildcard and "
                        "q-ordering (plus exclusion and garbage), and the "
                        "panel that shows the catalog state and the "
                        "policy. The stack is up; every command answers "
                        "from the real substrate this topic built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-absent",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — no Accept-Language at all: the default answers, visibly\n"
                        "curl -s localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"header:\", b[\"header\"], \"· locale:\", b[\"selectedLocale\"], \\\n"
                        "\"· fell back:\", b[\"fellBackToDefault\"]); \\\n"
                        "print(\"welcome:\", b[\"uiStrings\"][0][\"value\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-german",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the German region fallback: de-DE reaches de, everything changes\n"
                        "curl -s -H 'Accept-Language: de-DE,de;q=0.9,en;q=0.5' localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"locale:\", b[\"selectedLocale\"], \"via\", b[\"matchedVia\"]); \\\n"
                        "[print(\" \", r[\"raw\"], \"· q\", r[\"quality\"], \"·\", r[\"matchedVia\"], \"→\", r[\"matchedLocale\"]) for r in b[\"ranges\"]]; \\\n"
                        "print(\"welcome:\", b[\"uiStrings\"][0][\"value\"]); \\\n"
                        "print(\"number:\", b[\"formatting\"][\"number\"], \"· currency:\", b[\"formatting\"][\"currency\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-polish",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — Polish plurals: the category math, count by count\n"
                        "curl -s -H 'Accept-Language: pl' localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "[print(\" \", p[\"count\"], \"→\", p[\"category\"].ljust(5), p[\"sentence\"]) for p in b[\"plurals\"]]'\n"
                        "# zones: the same instant on three walls, labeled in Polish\n"
                        "curl -s -H 'Accept-Language: pl' localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "[print(\" \", z[\"zone\"], z[\"utcOffset\"], z[\"abbreviation\"], \"·\", z[\"formatted\"]) for z in b[\"zones\"]]'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-wildcard",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — wildcard, exclusion, and hostile junk: none of it is an error\n"
                        "curl -s -H 'Accept-Language: *' localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"wildcard →\", b[\"selectedLocale\"], \"via\", b[\"matchedVia\"])'\n"
                        "curl -s -H 'Accept-Language: en;q=0, *' localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"en excluded →\", b[\"selectedLocale\"], \"via\", b[\"matchedVia\"])'\n"
                        "curl -s -H 'Accept-Language: !!!, 1nvalid, pl;q=abc' localhost:8000/api/demo/i18n/negotiate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"junk skipped →\", b[\"selectedLocale\"], \"· ranges:\", [(r[\"tag\"], r[\"quality\"]) for r in b[\"ranges\"]])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the panel: policy, plural grammar per locale, catalog coverage\n"
                        "curl -s localhost:8000/api/demo/i18n \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); p=b[\"policy\"]; \\\n"
                        "print(\"default:\", p[\"defaultLocale\"], \"· instant:\", p[\"fixedInstant\"]); \\\n"
                        "[print(\" \", l[\"tag\"], l[\"nativeName\"], \"· plurals:\", \"/\".join(l[\"pluralCategories\"])) for l in p[\"supportedLocales\"]]; \\\n"
                        "print(\" untranslated in de:\", [r[\"msgid\"] for r in b[\"catalog\"] \\\n"
                        "  if any(not c[\"translated\"] for c in r[\"translations\"] if c[\"locale\"]==\"de\")])'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 1 shows the absent header answering the "
                        "default with the fallback FLAGGED — not guessed. "
                        "Stop 2 walks one header through the whole ranked "
                        "parse and watches every layer move together: "
                        "locale, strings, separators, currency placement. "
                        "Stop 3 is the grammar lesson — five counts, three "
                        "Polish categories, 5 and 22 taking different "
                        "forms — beside the same instant on three walls. "
                        "Stop 4 proves the hostile-input policy: wildcard, "
                        "exclusion, and junk all answer, none of them "
                        "error. Stop 5 reads the state of the translation "
                        "contract off the panel. Next the group goes "
                        "realtime — the SSE tickers and WebSocket rooms "
                        "of topic 28 push against the very edges this "
                        "topic formatted."
                    ),
                ),
            ],
        ),
    ],
)
