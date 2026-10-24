import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { StallPanel } from '../../domain/demo/debug-stall';
import type { DebugStallRepository } from '../../domain/demo/debug-stall-repository';
import type { DebugStallApi } from './debug-stall-api';

/**
 * DebugStallRepositoryImpl — adapts the stall API to the domain port.
 * A Failed Result means the panel itself broke (network down, unparseable
 * body); the diagnosis has no degraded server state to model beyond that.
 */
export class DebugStallRepositoryImpl implements DebugStallRepository {
  private readonly api: DebugStallApi;

  constructor(api: DebugStallApi) {
    this.api = api;
  }

  panel(): Promise<Result<StallPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
