import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from '../../domain/demo/auth-oauth';
import { stringList } from './auth-api-keys-dto';
import {
  isRecord,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * AuthOauthDTO — the wire/transport shapes of the OAuth lab: the flow map
 * plus the pkce pair, the authorize outcome (redirect + one-time code),
 * and the exchange outcome (the earned access token).
 */

/** Deserialize + validate the flow map. */
export function oauthPanelFromJson(body: unknown): OAuthPanel {
  if (!isRecord(body)) throw new Error('oauth panel must be an object');
  return {
    clientId: requiredString(body, 'clientId'),
    clientKind: requiredString(body, 'clientKind'),
    redirectUris: stringList(body, 'redirectUris'),
    clientScopes: stringList(body, 'clientScopes'),
    codeTtlSeconds: requiredNumber(body, 'codeTtlSeconds'),
    pkceNote: requiredString(body, 'pkceNote'),
    steps: stringList(body, 'steps'),
    pkceEndpoint: requiredString(body, 'pkceEndpoint'),
    authorizeEndpoint: requiredString(body, 'authorizeEndpoint'),
    tokenEndpoint: requiredString(body, 'tokenEndpoint'),
    protectedEndpoint: requiredString(body, 'protectedEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the pkce pair. */
export function pkcePairFromJson(body: unknown): PkcePair {
  if (!isRecord(body)) throw new Error('pkce pair must be an object');
  const method = requiredString(body, 'method');
  if (method !== 'S256') throw new Error(`unknown pkce method: ${method}`);
  return {
    verifier: requiredString(body, 'verifier'),
    codeChallenge: requiredString(body, 'codeChallenge'),
    method,
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the authorize outcome. */
export function authorizeOutcomeFromJson(body: unknown): AuthorizeOutcome {
  if (!isRecord(body)) throw new Error('authorize outcome must be an object');
  return {
    redirectTo: requiredString(body, 'redirectTo'),
    state: requiredString(body, 'state'),
    consent: requiredString(body, 'consent'),
    codePreview: requiredString(body, 'codePreview'),
    expiresIn: requiredNumber(body, 'expiresIn'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the exchange outcome. */
export function exchangeOutcomeFromJson(body: unknown): ExchangeOutcome {
  if (!isRecord(body)) throw new Error('exchange outcome must be an object');
  return {
    accessToken: requiredString(body, 'accessToken'),
    tokenType: requiredString(body, 'tokenType'),
    expiresIn: requiredNumber(body, 'expiresIn'),
    scope: requiredString(body, 'scope'),
    username: requiredString(body, 'username'),
    detail: requiredString(body, 'detail'),
  };
}
