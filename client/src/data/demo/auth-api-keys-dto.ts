import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
  KeyRecord,
} from '../../domain/demo/auth-api-keys';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredString,
} from '../content/validate';

/**
 * AuthApiKeysDTO — the wire/transport shapes of the key lab: the roster
 * payload (prefixes and hash previews only) plus the three action outcomes
 * (creation carries the raw key exactly once, by design).
 */

export function stringList(source: Record<string, unknown>, key: string): string[] {
  return requiredArray(source, key).map((value) => {
    if (typeof value !== 'string') throw new Error(`expected string list: ${key}`);
    return value;
  });
}

function keyRecordFromJson(value: unknown): KeyRecord {
  if (!isRecord(value)) throw new Error('key record must be an object');
  return {
    prefix: requiredString(value, 'prefix'),
    name: requiredString(value, 'name'),
    scopes: stringList(value, 'scopes'),
    keyHashPreview: requiredString(value, 'keyHashPreview'),
    createdAt: requiredString(value, 'createdAt'),
  };
}

/** Deserialize + validate the roster payload. */
export function apiKeysPanelFromJson(body: unknown): ApiKeysPanel {
  if (!isRecord(body)) throw new Error('api keys panel must be an object');
  return {
    records: requiredArray(body, 'records').map(keyRecordFromJson),
    storageNote: requiredString(body, 'storageNote'),
    lookupNote: requiredString(body, 'lookupNote'),
    createEndpoint: requiredString(body, 'createEndpoint'),
    callEndpoint: requiredString(body, 'callEndpoint'),
    revokeEndpoint: requiredString(body, 'revokeEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the creation outcome — the raw key's one appearance. */
export function apiKeyCreatedFromJson(body: unknown): ApiKeyCreated {
  if (!isRecord(body)) throw new Error('api key created must be an object');
  return {
    prefix: requiredString(body, 'prefix'),
    key: requiredString(body, 'key'),
    keyHash: requiredString(body, 'keyHash'),
    name: requiredString(body, 'name'),
    scopes: stringList(body, 'scopes'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the protected-call outcome. */
export function apiKeyCallFromJson(body: unknown): ApiKeyCallOutcome {
  if (!isRecord(body)) throw new Error('api key call must be an object');
  return {
    prefix: requiredString(body, 'prefix'),
    name: requiredString(body, 'name'),
    scopes: stringList(body, 'scopes'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the revoke outcome. */
export function apiKeyRevokeFromJson(body: unknown): ApiKeyRevokeOutcome {
  if (!isRecord(body)) throw new Error('api key revoke must be an object');
  return {
    prefix: requiredString(body, 'prefix'),
    revoked: requiredBoolean(body, 'revoked'),
    detail: requiredString(body, 'detail'),
  };
}
