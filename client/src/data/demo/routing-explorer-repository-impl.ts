import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { RoutingExplorerData, RoutingExplorerRequest } from '../../domain/demo/routing-explorer';
import type { RoutingExplorerRepository } from '../../domain/demo/routing-explorer-repository';
import { toRoutingExplorer } from './routing-explorer-dto';
import type { RoutingExplorerApi } from './routing-explorer-api';

/**
 * RoutingExplorerRepositoryImpl — adapts the explorer API to the domain
 * port. Every thrown transport error (network, non-2xx, malformed payload)
 * is guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class RoutingExplorerRepositoryImpl implements RoutingExplorerRepository {
  private readonly api: RoutingExplorerApi;

  constructor(api: RoutingExplorerApi) {
    this.api = api;
  }

  resolve(request: RoutingExplorerRequest): Promise<Result<RoutingExplorerData>> {
    return safeRepositoryCall(async () => toRoutingExplorer(await this.api.resolve(request)));
  }
}
