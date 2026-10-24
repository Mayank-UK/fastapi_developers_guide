import type { Result } from '../../core/result';
import type { StatelessPanel } from './scaling-stateless';

/**
 * ScalingStatelessRepository — the domain-facing port for the scaling
 * topic's live state-placement panel. Demo components depend on this
 * interface only; the HTTP adapter lives in data/demo and is wired at
 * the composition root.
 *
 * The panel is one honest 2xx read: the server snapshots the real
 * in-process facts off the composition root and walks the two-replica
 * round on the very request that serves it, so every row (flags,
 * counts, increments, placements) is the real substrate's output, never
 * a fabricated number.
 */
export interface ScalingStatelessRepository {
  /** The state-placement panel: two replicas, one shared counter. */
  panel(): Promise<Result<StatelessPanel>>;
}
