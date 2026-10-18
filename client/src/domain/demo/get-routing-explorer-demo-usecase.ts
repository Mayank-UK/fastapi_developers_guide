import type { Result } from '../../core/result';
import type { RoutingExplorerRepository } from './routing-explorer-repository';
import type { RoutingExplorerData, RoutingExplorerRequest } from './routing-explorer';

/**
 * GetRoutingExplorerDemoUseCase — resolves the routing topic's simulated
 * request line (react-guide use-case style): a thin orchestration seam
 * over the repository port. Carries the request parameters because this
 * demo is interactive — the user picks a method and a path; the server
 * replays the router's walk against the declared table.
 */
export class GetRoutingExplorerDemoUseCase {
  private readonly repository: RoutingExplorerRepository;

  constructor(repository: RoutingExplorerRepository) {
    this.repository = repository;
  }

  execute(request: RoutingExplorerRequest): Promise<Result<RoutingExplorerData>> {
    return this.repository.resolve(request);
  }
}
