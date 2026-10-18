import type {
  RefreshExchangeOutcome,
  RefreshFamily,
  RefreshLoginOutcome,
  RefreshPanel,
  RefreshTelemetry,
  RefreshTokenRow,
} from '../../domain/demo/auth-refresh';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * AuthRefreshDTO — the wire/transport shapes of the refresh lab: the
 * family board plus the login and exchange outcomes. Optional halves of an
 * exchange (tokens, positions) ride the wire as null when absent-on-purpose;
 * the DTO treats those nulls as honest absence, never as a bad field.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function numberOrNull(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'number') throw new Error(`expected number or null: ${key}`);
  return value;
}

function tokenRowFromJson(value: unknown): RefreshTokenRow {
  if (!isRecord(value)) throw new Error('refresh token row must be an object');
  return {
    position: requiredNumber(value, 'position'),
    status: requiredString(value, 'status'),
    issuedAt: requiredString(value, 'issuedAt'),
    usedAt: stringOrNull(value, 'usedAt'),
  };
}

function familyFromJson(value: unknown): RefreshFamily {
  if (!isRecord(value)) throw new Error('refresh family must be an object');
  return {
    familyId: requiredString(value, 'familyId'),
    username: requiredString(value, 'username'),
    status: requiredString(value, 'status'),
    createdAt: requiredString(value, 'createdAt'),
    tokens: requiredArray(value, 'tokens').map(tokenRowFromJson),
  };
}

/** Deserialize + validate the family board. */
export function refreshPanelFromJson(body: unknown): RefreshPanel {
  if (!isRecord(body)) throw new Error('refresh panel must be an object');
  const telemetry = requiredRecord(body, 'telemetry');
  const telemetryOut: RefreshTelemetry = {
    logins: requiredNumber(telemetry, 'logins'),
    rotations: requiredNumber(telemetry, 'rotations'),
    reuseEvents: requiredNumber(telemetry, 'reuseEvents'),
  };
  return {
    families: requiredArray(body, 'families').map(familyFromJson),
    telemetry: telemetryOut,
    patternNote: requiredString(body, 'patternNote'),
    loginEndpoint: requiredString(body, 'loginEndpoint'),
    exchangeEndpoint: requiredString(body, 'exchangeEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the login outcome (raw refresh token, once). */
export function refreshLoginFromJson(body: unknown): RefreshLoginOutcome {
  if (!isRecord(body)) throw new Error('refresh login must be an object');
  return {
    familyId: requiredString(body, 'familyId'),
    username: requiredString(body, 'username'),
    accessToken: requiredString(body, 'accessToken'),
    accessExpiresIn: requiredNumber(body, 'accessExpiresIn'),
    refreshToken: requiredString(body, 'refreshToken'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the exchange outcome — rotated or reuse-detected. */
export function refreshExchangeFromJson(body: unknown): RefreshExchangeOutcome {
  if (!isRecord(body)) throw new Error('refresh exchange must be an object');
  const outcome = requiredString(body, 'outcome');
  if (outcome !== 'rotated' && outcome !== 'reuse-detected' && outcome !== 'invalid') {
    throw new Error(`unknown refresh outcome: ${outcome}`);
  }
  return {
    outcome,
    familyId: stringOrNull(body, 'familyId'),
    accessToken: stringOrNull(body, 'accessToken'),
    accessExpiresIn: numberOrNull(body, 'accessExpiresIn'),
    refreshToken: stringOrNull(body, 'refreshToken'),
    rotatedFromPosition: numberOrNull(body, 'rotatedFromPosition'),
    familyTokensRevoked: requiredNumber(body, 'familyTokensRevoked'),
    detail: requiredString(body, 'detail'),
  };
}
