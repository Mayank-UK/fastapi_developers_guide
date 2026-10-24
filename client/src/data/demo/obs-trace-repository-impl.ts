import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { TraceFanout } from '../../domain/demo/obs-trace';
import type { ObsTraceRepository } from '../../domain/demo/obs-trace-repository';
import type { ObsTraceApi } from './obs-trace-api';

/**
 * ObsTraceRepositoryImpl — adapts the trace API to the domain port.
 * A Failed Result means the round itself broke (network down, unparseable
 * body); the fan-out has no degraded server state to model beyond that.
 */
export class ObsTraceRepositoryImpl implements ObsTraceRepository {
  private readonly api: ObsTraceApi;

  constructor(api: ObsTraceApi) {
    this.api = api;
  }

  fanout(): Promise<Result<TraceFanout>> {
    return safeRepositoryCall(() => this.api.fanout());
  }
}
