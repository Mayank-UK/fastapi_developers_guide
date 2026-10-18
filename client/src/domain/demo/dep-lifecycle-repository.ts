import type { Result } from '../../core/result';
import type { DepLifecycleLogData, DepLifecycleSpanData } from './dep-lifecycle';

/**
 * DepLifecycleRepository — the domain-facing port for the yield-dependency
 * lifecycle demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface DepLifecycleRepository {
  /** Fire one wrapped request; get the span facts the handler can know. */
  fire(): Promise<Result<DepLifecycleSpanData>>;
  /** Read the shared span log — the ordering proof, as data. */
  log(): Promise<Result<DepLifecycleLogData>>;
}
