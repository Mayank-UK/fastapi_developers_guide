import type { Result } from '../../core/result';
import type { BreakerPanel } from './reliability-breaker';
import type { ReliabilityBreakerRepository } from './reliability-breaker-repository';

/**
 * GetReliabilityBreakerDemoUseCase — the reliability topic's live circuit
 * breaker: one read where the server walks the real pure substrate
 * through a full cycle (closed → open → half-open → closed) with
 * per-call state, latency, and reason evidence — the open timeout
 * elapsing on an injected clock, only the bounded failure latency real.
 */
export class GetReliabilityBreakerDemoUseCase {
  private readonly repository: ReliabilityBreakerRepository;

  constructor(repository: ReliabilityBreakerRepository) {
    this.repository = repository;
  }

  /** The breaker: one full cycle, every verdict real, latencies measured. */
  panel(): Promise<Result<BreakerPanel>> {
    return this.repository.panel();
  }
}
