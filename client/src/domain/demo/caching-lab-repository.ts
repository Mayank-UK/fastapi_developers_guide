import type { Result } from '../../core/result';
import type {
  CachingLabDemo,
  ConditionalRound,
  InvalidationOutcome,
  StampedeOutcome,
} from './caching-lab';

/**
 * CachingLabRepository — the domain-facing port for the caching topic's
 * lab demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 * Four methods, one per lab action: the roster (state panel facts), the
 * raw conditional round against the REAL endpoint (200 or 304 — the
 * round a curl would see), explicit invalidation, and the stampede.
 */
export interface CachingLabRepository {
  /** Fetch the lab roster: key, TTL, cost label, endpoints, live state. */
  lab(): Promise<Result<CachingLabDemo>>;
  /**
   * One conditional round against the real endpoint; `ifNoneMatch` is
   * the ETag to send back (omitted on the first, fresh round).
   */
  conditionalRound(ifNoneMatch?: string): Promise<Result<ConditionalRound>>;
  /** Delete the cached entry; report what the next read will do. */
  invalidate(): Promise<Result<InvalidationOutcome>>;
  /** Fire N concurrent cold reads; single-flight answers the counts. */
  stampede(requests: number): Promise<Result<StampedeOutcome>>;
}
