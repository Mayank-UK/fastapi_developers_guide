import type { Result } from '../../core/result';
import type { LogViewerPanel } from './obs-viewer';

/**
 * ObsViewerRepository — the domain-facing port for the observability
 * topic's structured-log viewer. Demo components depend on this interface
 * only; the HTTP adapter lives in data/demo and is wired at the
 * composition root.
 *
 * The panel is one honest 2xx read of the server's real pipeline and
 * recent-events ring; there is no failure state to model beyond the round
 * itself (the ring may simply hold few events on a quiet process).
 */
export interface ObsViewerRepository {
  /** The panel: active pipeline, configured level, the ring's real events. */
  panel(): Promise<Result<LogViewerPanel>>;
}
