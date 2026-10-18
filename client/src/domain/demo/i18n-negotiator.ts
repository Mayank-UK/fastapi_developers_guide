/**
 * Domain models for the i18n topic's negotiator (demo block id
 * `i18n:negotiator`) — the client-side shape of the /api/demo/i18n*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The panel carries the policy and the catalog state; a ROUND is one
 * Accept-Language header answered in full — the ranked parse, the
 * negotiated locale, and everything that locale changes downstream
 * (strings, formatting, plural categories, wall clocks).
 */

/** One servable locale: display names and plural grammar from CLDR data. */
export interface LocaleRow {
  tag: string;
  englishName: string;
  nativeName: string;
  pluralCategories: string[];
}

/** One message in one catalog locale: what serves, and whether it fell back. */
export interface CatalogCellRow {
  locale: string;
  served: string;
  translated: boolean;
}

/** One message's row in the panel's catalog table (source beside translations). */
export interface CatalogRow {
  msgid: string;
  translations: CatalogCellRow[];
}

/** The demo's fixed facts: default locale, servable set, inputs, counts. */
export interface I18nPolicy {
  defaultLocale: string;
  supportedLocales: LocaleRow[];
  fixedInstant: string;
  numberInput: number;
  currencyCode: string;
  currencyAmount: number;
  pluralCounts: number[];
}

/** One demo endpoint on the tour: path, method, what it teaches. */
export interface I18nEndpointRow {
  path: string;
  method: string;
  teaches: string;
}

/** Wire shape of GET /api/demo/i18n — the negotiator panel's contract. */
export interface I18nPanel {
  policy: I18nPolicy;
  catalog: CatalogRow[];
  endpoints: I18nEndpointRow[];
  honestyNotes: string[];
  reasoning: string;
}

/** One element of the ranked parse: as sent, normalized, q, and its fate. */
export interface NegotiationRangeRow {
  raw: string;
  tag: string;
  quality: number;
  matchedLocale: string | null;
  matchedVia: string;
}

/** One served UI string: the source message beside the localized value. */
export interface UiStringRow {
  msgid: string;
  value: string;
}

/** The fixed inputs rendered by the negotiated locale. */
export interface FormattingRow {
  numberInput: number;
  number: string;
  currencyCode: string;
  currencyAmount: number;
  currency: string;
  instant: string;
  date: string;
}

/** One count: CLDR category beside the correctly pluralized sentence. */
export interface PluralRow {
  count: number;
  category: string;
  sentence: string;
}

/** The fixed instant on one wall clock, labeled by the negotiated locale. */
export interface ZoneRow {
  zone: string;
  wallTime: string;
  utcOffset: string;
  abbreviation: string;
  formatted: string;
}

/** Wire shape of GET /api/demo/i18n/negotiate — one header, fully answered. */
export interface NegotiatorRound {
  header: string | null;
  selectedLocale: string;
  matchedVia: string;
  fellBackToDefault: boolean;
  ranges: NegotiationRangeRow[];
  uiStrings: UiStringRow[];
  formatting: FormattingRow;
  plurals: PluralRow[];
  zones: ZoneRow[];
}
