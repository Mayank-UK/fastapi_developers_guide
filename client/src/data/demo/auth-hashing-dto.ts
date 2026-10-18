import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
  SeedCredential,
} from '../../domain/demo/auth-hashing';
import { stringList } from './auth-api-keys-dto';
import {
  isRecord,
  requiredBoolean,
  requiredNumber,
  requiredArray,
  requiredString,
} from '../content/validate';

/**
 * AuthHashingDTO — the wire/transport shapes of the hashing lab: the
 * contract panel (active + legacy cost, seeded credential previews) plus
 * the hash and verify outcomes (real elapsed milliseconds, honest verdicts).
 */

function seedCredentialFromJson(value: unknown): SeedCredential {
  if (!isRecord(value)) throw new Error('seed credential must be an object');
  return {
    username: requiredString(value, 'username'),
    displayName: requiredString(value, 'displayName'),
    hashPreview: requiredString(value, 'hashPreview'),
    scopes: stringList(value, 'scopes'),
  };
}

/** Deserialize + validate the contract panel. */
export function hashingPanelFromJson(body: unknown): HashingPanel {
  if (!isRecord(body)) throw new Error('hashing panel must be an object');
  return {
    algorithm: requiredString(body, 'algorithm'),
    parameters: requiredString(body, 'parameters'),
    legacyParameters: requiredString(body, 'legacyParameters'),
    seedCredentials: requiredArray(body, 'seedCredentials').map(seedCredentialFromJson),
    distinctionNote: requiredString(body, 'distinctionNote'),
    loggingNote: requiredString(body, 'loggingNote'),
    hashEndpoint: requiredString(body, 'hashEndpoint'),
    verifyEndpoint: requiredString(body, 'verifyEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the hash outcome. */
export function passwordHashFromJson(body: unknown): PasswordHashOutcome {
  if (!isRecord(body)) throw new Error('password hash must be an object');
  return {
    hash: requiredString(body, 'hash'),
    algorithm: requiredString(body, 'algorithm'),
    parameters: requiredString(body, 'parameters'),
    elapsedMs: requiredNumber(body, 'elapsedMs'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the verify outcome (error is honest-null-able). */
export function passwordVerifyFromJson(body: unknown): PasswordVerifyOutcome {
  if (!isRecord(body)) throw new Error('password verify must be an object');
  const error = body['error'];
  if (error !== null && typeof error !== 'string') {
    throw new Error('expected string or null: error');
  }
  return {
    ok: requiredBoolean(body, 'ok'),
    needsRehash: requiredBoolean(body, 'needsRehash'),
    elapsedMs: requiredNumber(body, 'elapsedMs'),
    error,
    detail: requiredString(body, 'detail'),
  };
}
