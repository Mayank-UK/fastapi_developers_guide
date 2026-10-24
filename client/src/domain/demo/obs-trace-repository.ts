import type { Result } from '../../core/result';
import type { TraceFanout } from './obs-trace';

/**
 * ObsTraceRepository — the domain-facing port for the observability
 * topic's trace fan-out. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root.
 *
 * The fan-out is one honest 2xx read: the server drives the three real
 * rounds when the request arrives and reports what really happened,
 * measured only at the ASGI boundary beats.
 */
export interface ObsTraceRepository {
  /** The fan-out: the trace root, the three real rounds, the correlation. */
  fanout(): Promise<Result<TraceFanout>>;
}
