import type {
  BurnOutcome,
  CorsPolicyRow,
  HeaderNoteRow,
  RateLimitPolicyRow,
  SecurityLabPanel,
} from '../../domain/demo/security-lab';
import { isRecord, requiredArray, requiredBoolean, requiredNumber, requiredString } from '../content/validate';

/**
 * SecurityLabDTO — the wire/transport shapes of the security lab: the
 * panel (header table with the WHY for each entry, the CORS policy, the
 * throttle policy) and one allowed burn round. The throttled round is not
 * a DTO — it is shaped from the raw 429 response (status + Retry-After
 * header + envelope message) inside the API, because a 429 has no 2xx body
 * to validate.
 */

function stringList(source: Record<string, unknown>, key: string): string[] {
  const values = requiredArray(source, key);
  return values.map((value) => {
    if (typeof value !== 'string') throw new Error(`expected string list at "${key}"`);
    return value;
  });
}

function headerNoteFromJson(value: unknown): HeaderNoteRow {
  if (!isRecord(value)) throw new Error('header note must be an object');
  return {
    header: requiredString(value, 'header'),
    value: requiredString(value, 'value'),
    why: requiredString(value, 'why'),
  };
}

function corsPolicyFromJson(value: unknown): CorsPolicyRow {
  if (!isRecord(value)) throw new Error('cors policy must be an object');
  return {
    allowedOrigins: stringList(value, 'allowedOrigins'),
    allowCredentials: requiredBoolean(value, 'allowCredentials'),
    allowedMethods: stringList(value, 'allowedMethods'),
    allowedHeaders: stringList(value, 'allowedHeaders'),
    preflightMaxAgeS: requiredNumber(value, 'preflightMaxAgeS'),
    misconfigNote: requiredString(value, 'misconfigNote'),
  };
}

function rateLimitPolicyFromJson(value: unknown): RateLimitPolicyRow {
  if (!isRecord(value)) throw new Error('rate limit policy must be an object');
  return {
    windowSeconds: requiredNumber(value, 'windowSeconds'),
    budget: requiredNumber(value, 'budget'),
    keying: requiredString(value, 'keying'),
    burnEndpoint: requiredString(value, 'burnEndpoint'),
    whyPublicEndpoints: requiredString(value, 'whyPublicEndpoints'),
  };
}

/** Deserialize + validate the lab panel. */
export function securityLabPanelFromJson(body: unknown): SecurityLabPanel {
  if (!isRecord(body)) throw new Error('security lab panel must be an object');
  const cors = body['cors'];
  const rateLimit = body['rateLimit'];
  if (!isRecord(cors)) throw new Error('cors must be an object');
  if (!isRecord(rateLimit)) throw new Error('rateLimit must be an object');
  return {
    headers: requiredArray(body, 'headers').map(headerNoteFromJson),
    cors: corsPolicyFromJson(cors),
    rateLimit: rateLimitPolicyFromJson(rateLimit),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate one allowed burn round. */
export function burnOutcomeFromJson(body: unknown): BurnOutcome {
  if (!isRecord(body)) throw new Error('burn outcome must be an object');
  return {
    attempt: requiredNumber(body, 'attempt'),
    remaining: requiredNumber(body, 'remaining'),
    limit: requiredNumber(body, 'limit'),
    windowSeconds: requiredNumber(body, 'windowSeconds'),
    detail: requiredString(body, 'detail'),
  };
}
