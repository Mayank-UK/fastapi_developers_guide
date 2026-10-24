import type { Result } from '../../core/result';
import type { ObsViewerRepository } from './obs-viewer-repository';
import type { LogViewerPanel } from './obs-viewer';

/**
 * GetObsViewerDemoUseCase — the observability topic's structured-log
 * viewer: one live read of the server's REAL structlog pipeline (the
 * active processor chain, introspected) and the recent-events ring it
 * feeds — every row a real logged event, correlated by request id.
 */
export class GetObsViewerDemoUseCase {
  private readonly repository: ObsViewerRepository;

  constructor(repository: ObsViewerRepository) {
    this.repository = repository;
  }

  /** The panel: active pipeline, configured level, the ring's real events. */
  panel(): Promise<Result<LogViewerPanel>> {
    return this.repository.panel();
  }
}
