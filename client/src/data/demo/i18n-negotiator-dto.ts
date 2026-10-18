import type {
  CatalogCellRow,
  CatalogRow,
  FormattingRow,
  I18nEndpointRow,
  I18nPanel,
  LocaleRow,
  NegotiationRangeRow,
  NegotiatorRound,
  PluralRow,
  UiStringRow,
  ZoneRow,
} from '../../domain/demo/i18n-negotiator';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * I18nNegotiatorDTO — the wire/transport shapes of the negotiator's two
 * JSON endpoints (panel, negotiate), validated field-by-field so a shape
 * violation surfaces as a typed invalid_response failure instead of
 * "[object Object]" reaching the UI. Nullable-by-contract fields (the
 * absent header, an unmatched range) are the only nulls on the wire.
 */

function localeRowFromJson(value: unknown): LocaleRow {
  if (!isRecord(value)) throw new Error('locale row must be an object');
  return {
    tag: requiredString(value, 'tag'),
    englishName: requiredString(value, 'englishName'),
    nativeName: requiredString(value, 'nativeName'),
    pluralCategories: requiredArray(value, 'pluralCategories').map((entry) => {
      if (typeof entry !== 'string') throw new Error('plural categories must be strings');
      return entry;
    }),
  };
}

function catalogCellFromJson(value: unknown): CatalogCellRow {
  if (!isRecord(value)) throw new Error('catalog cell must be an object');
  return {
    locale: requiredString(value, 'locale'),
    served: requiredString(value, 'served'),
    translated: requiredBoolean(value, 'translated'),
  };
}

function catalogRowFromJson(value: unknown): CatalogRow {
  if (!isRecord(value)) throw new Error('catalog row must be an object');
  return {
    msgid: requiredString(value, 'msgid'),
    translations: requiredArray(value, 'translations').map(catalogCellFromJson),
  };
}

function endpointFromJson(value: unknown): I18nEndpointRow {
  if (!isRecord(value)) throw new Error('endpoint row must be an object');
  return {
    path: requiredString(value, 'path'),
    method: requiredString(value, 'method'),
    teaches: requiredString(value, 'teaches'),
  };
}

/** Deserialize + validate the negotiator panel. */
export function i18nPanelFromJson(body: unknown): I18nPanel {
  if (!isRecord(body)) throw new Error('i18n panel must be an object');
  const policy = body['policy'];
  if (!isRecord(policy)) throw new Error('policy must be an object');
  const honestyNotes = requiredArray(body, 'honestyNotes').map((note) => {
    if (typeof note !== 'string') throw new Error('honesty notes must be strings');
    return note;
  });
  return {
    policy: {
      defaultLocale: requiredString(policy, 'defaultLocale'),
      supportedLocales: requiredArray(policy, 'supportedLocales').map(localeRowFromJson),
      fixedInstant: requiredString(policy, 'fixedInstant'),
      numberInput: requiredNumber(policy, 'numberInput'),
      currencyCode: requiredString(policy, 'currencyCode'),
      currencyAmount: requiredNumber(policy, 'currencyAmount'),
      pluralCounts: requiredArray(policy, 'pluralCounts').map((entry) => {
        if (typeof entry !== 'number') throw new Error('plural counts must be numbers');
        return entry;
      }),
    },
    catalog: requiredArray(body, 'catalog').map(catalogRowFromJson),
    endpoints: requiredArray(body, 'endpoints').map(endpointFromJson),
    honestyNotes,
    reasoning: requiredString(body, 'reasoning'),
  };
}

function rangeFromJson(value: unknown): NegotiationRangeRow {
  if (!isRecord(value)) throw new Error('range row must be an object');
  const matchedLocale = value['matchedLocale'];
  if (matchedLocale !== null && typeof matchedLocale !== 'string') {
    throw new Error('matchedLocale must be a string or null');
  }
  return {
    raw: requiredString(value, 'raw'),
    tag: requiredString(value, 'tag'),
    quality: requiredNumber(value, 'quality'),
    matchedLocale,
    matchedVia: requiredString(value, 'matchedVia'),
  };
}

function uiStringFromJson(value: unknown): UiStringRow {
  if (!isRecord(value)) throw new Error('ui string row must be an object');
  return {
    msgid: requiredString(value, 'msgid'),
    value: requiredString(value, 'value'),
  };
}

function formattingFromJson(value: unknown): FormattingRow {
  if (!isRecord(value)) throw new Error('formatting row must be an object');
  return {
    numberInput: requiredNumber(value, 'numberInput'),
    number: requiredString(value, 'number'),
    currencyCode: requiredString(value, 'currencyCode'),
    currencyAmount: requiredNumber(value, 'currencyAmount'),
    currency: requiredString(value, 'currency'),
    instant: requiredString(value, 'instant'),
    date: requiredString(value, 'date'),
  };
}

function pluralFromJson(value: unknown): PluralRow {
  if (!isRecord(value)) throw new Error('plural row must be an object');
  return {
    count: requiredNumber(value, 'count'),
    category: requiredString(value, 'category'),
    sentence: requiredString(value, 'sentence'),
  };
}

function zoneFromJson(value: unknown): ZoneRow {
  if (!isRecord(value)) throw new Error('zone row must be an object');
  return {
    zone: requiredString(value, 'zone'),
    wallTime: requiredString(value, 'wallTime'),
    utcOffset: requiredString(value, 'utcOffset'),
    abbreviation: requiredString(value, 'abbreviation'),
    formatted: requiredString(value, 'formatted'),
  };
}

/** Deserialize + validate one negotiation round. */
export function negotiatorRoundFromJson(body: unknown): NegotiatorRound {
  if (!isRecord(body)) throw new Error('negotiator round must be an object');
  const header = body['header'];
  if (header !== null && typeof header !== 'string') {
    throw new Error('header must be a string or null');
  }
  const formatting = body['formatting'];
  if (!isRecord(formatting)) throw new Error('formatting must be an object');
  return {
    header,
    selectedLocale: requiredString(body, 'selectedLocale'),
    matchedVia: requiredString(body, 'matchedVia'),
    fellBackToDefault: requiredBoolean(body, 'fellBackToDefault'),
    ranges: requiredArray(body, 'ranges').map(rangeFromJson),
    uiStrings: requiredArray(body, 'uiStrings').map(uiStringFromJson),
    formatting: formattingFromJson(formatting),
    plurals: requiredArray(body, 'plurals').map(pluralFromJson),
    zones: requiredArray(body, 'zones').map(zoneFromJson),
  };
}
