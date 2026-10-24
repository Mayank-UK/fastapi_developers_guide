import type { Result } from '../../core/result';
import type { PerfBenchPanel } from './perf-bench';

/**
 * PerfBenchRepository — the domain-facing port for the performance
 * topic's live bench. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 *
 * The panel is one honest 2xx read: the server measures everything on
 * the request that serves it (compression bytes and timings, the hygiene
 * comparison, loop/pool/GC introspection), never a cached or fabricated
 * number.
 */
export interface PerfBenchRepository {
  /** The bench: measured compression, hygiene, loop, pool, GC rows. */
  panel(): Promise<Result<PerfBenchPanel>>;
}
