import type {
  BearerResource,
  ClaimRow,
  JwtPanel,
  MintedToken,
  TokenLoginOutcome,
  TokenOutcome,
  TokenVerifyOutcome,
} from '../../domain/demo/auth-jwt';
import { stringList } from './auth-api-keys-dto';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * AuthJwtDTO — the wire/transport shapes of the token lab: the anatomy
 * panel plus the login, mint, verify, and protected outcomes. Optional
 * halves (username, scopes, expiresAt on a failed verify) ride the wire as
 * null when absent-on-purpose; the DTO treats those nulls as honest
 * absence, never as a bad field.
 */

const OUTCOMES: readonly TokenOutcome[] = [
  'valid',
  'expired',
  'not-yet-valid',
  'bad-signature',
  'malformed',
];

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function stringListOrNull(source: Record<string, unknown>, key: string): string[] | null {
  const value = source[key];
  if (value === null) return null;
  if (!Array.isArray(value)) throw new Error(`expected string list or null: ${key}`);
  return value.map((item) => {
    if (typeof item !== 'string') throw new Error(`expected string list: ${key}`);
    return item;
  });
}

/** Deserialize + validate the anatomy panel. */
export function jwtPanelFromJson(body: unknown): JwtPanel {
  if (!isRecord(body)) throw new Error('jwt panel must be an object');
  const claims = requiredArray(body, 'claims').map((value) => {
    if (!isRecord(value)) throw new Error('claim row must be an object');
    const row: ClaimRow = {
      claim: requiredString(value, 'claim'),
      meaning: requiredString(value, 'meaning'),
    };
    return row;
  });
  return {
    algorithm: requiredString(body, 'algorithm'),
    issuer: requiredString(body, 'issuer'),
    defaultTtlSeconds: requiredNumber(body, 'defaultTtlSeconds'),
    claims,
    loginEndpoint: requiredString(body, 'loginEndpoint'),
    mintEndpoint: requiredString(body, 'mintEndpoint'),
    verifyEndpoint: requiredString(body, 'verifyEndpoint'),
    protectedEndpoint: requiredString(body, 'protectedEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the form-login outcome. */
export function tokenLoginFromJson(body: unknown): TokenLoginOutcome {
  if (!isRecord(body)) throw new Error('token login must be an object');
  return {
    accessToken: requiredString(body, 'accessToken'),
    tokenType: requiredString(body, 'tokenType'),
    expiresIn: requiredNumber(body, 'expiresIn'),
    scope: requiredString(body, 'scope'),
    username: requiredString(body, 'username'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the mint outcome (header + payload decoded). */
export function mintedTokenFromJson(body: unknown): MintedToken {
  if (!isRecord(body)) throw new Error('minted token must be an object');
  const header = requiredRecord(body, 'header');
  const payload = requiredRecord(body, 'payload');
  const signedWith = requiredString(body, 'signedWith');
  if (signedWith !== 'real' && signedWith !== 'wrong') {
    throw new Error(`unknown signedWith: ${signedWith}`);
  }
  const headerOut: Record<string, string> = {};
  for (const [key, value] of Object.entries(header)) {
    if (typeof value !== 'string') throw new Error('header values must be strings');
    headerOut[key] = value;
  }
  return {
    token: requiredString(body, 'token'),
    header: headerOut,
    payload,
    signedWith,
    expiresAt: requiredString(body, 'expiresAt'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the verify verdict. */
export function tokenVerifyFromJson(body: unknown): TokenVerifyOutcome {
  if (!isRecord(body)) throw new Error('token verify must be an object');
  const outcome = requiredString(body, 'outcome') as TokenOutcome;
  if (!OUTCOMES.includes(outcome)) throw new Error(`unknown outcome: ${outcome}`);
  return {
    outcome,
    username: stringOrNull(body, 'username'),
    scopes: stringListOrNull(body, 'scopes'),
    expiresAt: stringOrNull(body, 'expiresAt'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the protected-resource outcome. */
export function bearerResourceFromJson(body: unknown): BearerResource {
  if (!isRecord(body)) throw new Error('bearer resource must be an object');
  return {
    username: requiredString(body, 'username'),
    scopes: stringList(body, 'scopes'),
    via: requiredString(body, 'via'),
    detail: requiredString(body, 'detail'),
  };
}
