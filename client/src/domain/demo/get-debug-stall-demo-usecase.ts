import type { Result } from '../../core/result';
import type { StallPanel } from './debug-stall';
import type { DebugStallRepository } from './debug-stall-repository';

/**
 * GetDebugStallDemoUseCase — the debugging topic's stall diagnosis: one
 * live read where the server runs four bounded phases (baseline, async
 * await, threadpool block, on-loop block) and reports the measured
 * evidence for each — elapsed, loop lag, a concurrent REAL /api/health,
 * a tracemalloc window, and this request's correlated log rows.
 */
export class GetDebugStallDemoUseCase {
  private readonly repository: DebugStallRepository;

  constructor(repository: DebugStallRepository) {
    this.repository = repository;
  }

  /** The diagnosis: four bounded phases, real measurements, correlated rows. */
  panel(): Promise<Result<StallPanel>> {
    return this.repository.panel();
  }
}
