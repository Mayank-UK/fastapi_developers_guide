import type { Result } from '../../core/result';
import type { RoutingExplorerData, RoutingExplorerRequest } from './routing-explorer';

/**
 * RoutingExplorerRepository — the domain-facing port for the routing
 * explorer demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface RoutingExplorerRepository {
  /** Resolve one simulated method+path against the declared route table. */
  resolve(request: RoutingExplorerRequest): Promise<Result<RoutingExplorerData>>;
}
