import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { LogViewerPanel } from '../../domain/demo/obs-viewer';
import type { ObsViewerRepository } from '../../domain/demo/obs-viewer-repository';
import type { ObsViewerApi } from './obs-viewer-api';

/**
 * ObsViewerRepositoryImpl — adapts the viewer API to the domain port.
 * A Failed Result means the round itself broke (network down, unparseable
 * body); the panel has no degraded server state to model beyond that.
 */
export class ObsViewerRepositoryImpl implements ObsViewerRepository {
  private readonly api: ObsViewerApi;

  constructor(api: ObsViewerApi) {
    this.api = api;
  }

  panel(): Promise<Result<LogViewerPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
