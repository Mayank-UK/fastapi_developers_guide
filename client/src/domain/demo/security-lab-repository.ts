import type { Result } from '../../core/result';
import type { BurnResult, SecurityLabLoad } from './security-lab';

/**
 * SecurityLabRepository — the domain-facing port for the security topic's
 * lab. Demo components depend on this interface only; the HTTP adapter
 * lives in data/demo and is wired at the composition root.
 *
 * `panel` also reports the response headers its own fetch OBSERVED, so the
 * demo can show what the live middleware actually stamped beside the
 * documented table. `burn` returns the throttle as a typed SUCCESS shape —
 * the 429 with its Retry-After is the outcome the lab exists to produce.
 */
export interface SecurityLabRepository {
  /** The panel (header table, CORS policy, throttle policy) + observed headers. */
  panel(): Promise<Result<SecurityLabLoad>>;
  /** Burn one unit: the remaining budget, or the 429 throttle itself. */
  burn(): Promise<Result<BurnResult>>;
}
