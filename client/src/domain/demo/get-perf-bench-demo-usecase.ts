import type { Result } from '../../core/result';
import type { PerfBenchPanel } from './perf-bench';
import type { PerfBenchRepository } from './perf-bench-repository';

/**
 * GetPerfBenchDemoUseCase — the performance topic's live bench: one read
 * where the server measures real gzip over the bytes this API serves,
 * runs the on-loop vs threadpool hygiene comparison with live probes,
 * introspects uvicorn's auto-selected loop and parser, snapshots the
 * engine pool, and reads the stdlib GC — every number computed at
 * request time.
 */
export class GetPerfBenchDemoUseCase {
  private readonly repository: PerfBenchRepository;

  constructor(repository: PerfBenchRepository) {
    this.repository = repository;
  }

  /** The bench: measured compression, hygiene, loop, pool, GC rows. */
  panel(): Promise<Result<PerfBenchPanel>> {
    return this.repository.panel();
  }
}
