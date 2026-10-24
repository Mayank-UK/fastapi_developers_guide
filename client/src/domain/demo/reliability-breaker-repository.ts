import type { Result } from '../../core/result';
import type { BreakerPanel } from './reliability-breaker';

/**
 * ReliabilityBreakerRepository — the domain-facing port for the
 * reliability topic's live circuit-breaker cycle. Demo components depend
 * on this interface only; the HTTP adapter lives in data/demo and is
 * wired at the composition root.
 *
 * The panel is one honest 2xx read: the server walks the real pure
 * CircuitBreaker substrate through a full cycle on the very request that
 * serves it, so every row (states, verdicts, latencies, reasons) is the
 * substrate's output, never a fabricated number.
 */
export interface ReliabilityBreakerRepository {
  /** The breaker: one full cycle, every verdict real, latencies measured. */
  panel(): Promise<Result<BreakerPanel>>;
}
