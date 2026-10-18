/**
 * Domain models for the caching topic's lab (demo block id `caching:lab`)
 * — the client-side shape of the /api/demo/caching/* endpoints. Field
 * names match the server's camelCase wire contract 1:1.
 *
 * The lab is interactive: one roster payload (the state panel's facts)
 * plus three actions — fetch the REAL conditional endpoint (whose round
 * is reported as a raw HTTP exchange: status, validators, body size),
 * invalidate explicitly, and fire a stampede whose counts prove
 * single-flight. The simulated origin cost is labeled by the server and
 * carried through untouched.
 */

/** What served one cache-aside read (coalesced only appears under load). */
export type CacheOutcome = 'hit' | 'miss' | 'coalesced';

/** The lab's in-process counters, snapshot at one interaction's end. */
export interface CacheTelemetry {
  hits: number;
  misses: number;
  coalesced: number;
  invalidations: number;
}

/** The state panel's facts: the key, its liveness, its size, counters. */
export interface CacheState {
  key: string;
  present: boolean;
  ttlSeconds: number;
  ttlRemainingS: number | null;
  sizeBytes: number | null;
  etag: string | null;
  lastOutcome: CacheOutcome | null;
  telemetry: CacheTelemetry;
}

/** Wire shape of GET /api/demo/caching/lab — the state panel's roster. */
export interface CachingLabDemo {
  namespace: string;
  key: string;
  ttlSeconds: number;
  originCostMs: number;
  originCostNote: string;
  postsEndpoint: string;
  invalidateEndpoint: string;
  stampedeEndpoint: string;
  state: CacheState;
  reasoning: string;
}

/** Wire shape of POST /api/demo/caching/invalidate. */
export interface InvalidationOutcome {
  key: string;
  deletedEntries: number;
  telemetry: CacheTelemetry;
  detail: string;
}

/** One request inside a stampede round, in launch order. */
export interface StampedeRoundRow {
  index: number;
  outcome: CacheOutcome;
  elapsedMs: number;
}

/** Wire shape of POST /api/demo/caching/stampede — single-flight proof. */
export interface StampedeOutcome {
  requests: number;
  originFetches: number;
  servedWarm: number;
  wallMs: number;
  rounds: StampedeRoundRow[];
  proof: string;
}

/**
 * One RAW conditional round against the real endpoint: exactly the facts
 * a curl of the same URL would show. A 304 reports an empty body and the
 * same validators; a 200 reports the served bytes' length. The elapsed
 * milliseconds are the server's own cache-side timing (the x-cache-
 * elapsed-ms header), not the browser's round-trip clock.
 */
export interface ConditionalRound {
  status: 200 | 304;
  etag: string;
  cacheControl: string;
  cache: CacheOutcome;
  elapsedMs: number;
  ageMs: number | null;
  originFetches: number;
  hits: number;
  bodyBytes: number;
}
