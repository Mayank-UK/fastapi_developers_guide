import type { Result } from '../../core/result';
import type { StallPanel } from './debug-stall';

/**
 * DebugStallRepository — the domain-facing port for the debugging
 * topic's stall diagnosis. Demo components depend on this interface
 * only; the HTTP adapter lives in data/demo and is wired at the
 * composition root.
 *
 * The panel is one honest 2xx read: the server runs the four bounded
 * phases when the request arrives and reports what really happened,
 * measured — never wedging the shared event loop.
 */
export interface DebugStallRepository {
  /** The diagnosis: four bounded phases, real measurements, correlated rows. */
  panel(): Promise<Result<StallPanel>>;
}
