import {
  type CacheOutcome,
  type CacheState,
  type CachingLabDemo,
  type InvalidationOutcome,
  type StampedeOutcome,
  type StampedeRoundRow,
} from '../../domain/demo/caching-lab';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * CachingLabDTO — the wire/transport shapes of the caching lab: the
 * roster payload (state panel facts), the invalidation outcome, and the
 * stampede proof. The conditional round is a RAW HTTP exchange (status,
 * validators, byte length); the api layer shapes it straight from the
 * response and shares the outcome validator below.
 */

const OUTCOMES = ['hit', 'miss', 'coalesced'] as const;

/** Parse one x-cache outcome; the server's vocabulary is closed. */
export function cacheOutcomeFromJson(value: unknown): CacheOutcome {
  if (typeof value !== 'string') throw new Error('cache outcome must be a string');
  if (!OUTCOMES.includes(value as (typeof OUTCOMES)[number])) {
    throw new Error(`unknown cache outcome: ${value}`);
  }
  return value as CacheOutcome;
}

function telemetryFromJson(source: Record<string, unknown>) {
  const telemetry = requiredRecord(source, 'telemetry');
  return {
    hits: requiredNumber(telemetry, 'hits'),
    misses: requiredNumber(telemetry, 'misses'),
    coalesced: requiredNumber(telemetry, 'coalesced'),
    invalidations: requiredNumber(telemetry, 'invalidations'),
  };
}

function numberOrNull(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  // null rides the wire when there is nothing to report (no countdown, no
  // size); the DTO treats it as absent-on-purpose, never as a bad field.
  if (value === null) return null;
  if (typeof value !== 'number') throw new Error(`expected number or null: ${key}`);
  return value;
}

function stateFromJson(body: Record<string, unknown>): CacheState {
  const state = requiredRecord(body, 'state');
  const etag = state['etag'];
  const lastOutcome = state['lastOutcome'];
  return {
    key: requiredString(state, 'key'),
    present: state['present'] === true,
    ttlSeconds: requiredNumber(state, 'ttlSeconds'),
    ttlRemainingS: numberOrNull(state, 'ttlRemainingS'),
    sizeBytes: numberOrNull(state, 'sizeBytes'),
    etag: etag === null || etag === undefined ? null : requiredString(state, 'etag'),
    lastOutcome:
      lastOutcome === null || lastOutcome === undefined
        ? null
        : cacheOutcomeFromJson(lastOutcome),
    telemetry: telemetryFromJson(state),
  };
}

/** Deserialize + validate the lab roster payload. */
export function cachingLabFromJson(body: unknown): CachingLabDemo {
  if (!isRecord(body)) throw new Error('caching lab must be an object');
  return {
    namespace: requiredString(body, 'namespace'),
    key: requiredString(body, 'key'),
    ttlSeconds: requiredNumber(body, 'ttlSeconds'),
    originCostMs: requiredNumber(body, 'originCostMs'),
    originCostNote: requiredString(body, 'originCostNote'),
    postsEndpoint: requiredString(body, 'postsEndpoint'),
    invalidateEndpoint: requiredString(body, 'invalidateEndpoint'),
    stampedeEndpoint: requiredString(body, 'stampedeEndpoint'),
    state: stateFromJson(body),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the invalidation outcome. */
export function invalidationFromJson(body: unknown): InvalidationOutcome {
  if (!isRecord(body)) throw new Error('invalidation outcome must be an object');
  return {
    key: requiredString(body, 'key'),
    deletedEntries: requiredNumber(body, 'deletedEntries'),
    telemetry: telemetryFromJson(body),
    detail: requiredString(body, 'detail'),
  };
}

function stampedeRoundFromJson(value: unknown): StampedeRoundRow {
  if (!isRecord(value)) throw new Error('stampede round row must be an object');
  return {
    index: requiredNumber(value, 'index'),
    outcome: cacheOutcomeFromJson(value['outcome']),
    elapsedMs: requiredNumber(value, 'elapsedMs'),
  };
}

/** Deserialize + validate the stampede outcome. */
export function stampedeFromJson(body: unknown): StampedeOutcome {
  if (!isRecord(body)) throw new Error('stampede outcome must be an object');
  return {
    requests: requiredNumber(body, 'requests'),
    originFetches: requiredNumber(body, 'originFetches'),
    servedWarm: requiredNumber(body, 'servedWarm'),
    wallMs: requiredNumber(body, 'wallMs'),
    rounds: requiredArray(body, 'rounds').map(stampedeRoundFromJson),
    proof: requiredString(body, 'proof'),
  };
}
