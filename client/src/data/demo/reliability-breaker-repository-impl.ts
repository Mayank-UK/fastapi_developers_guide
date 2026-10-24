import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { BreakerPanel } from '../../domain/demo/reliability-breaker';
import type { ReliabilityBreakerRepository } from '../../domain/demo/reliability-breaker-repository';
import type { ReliabilityBreakerApi } from './reliability-breaker-api';

/**
 * ReliabilityBreakerRepositoryImpl — adapts the breaker API to the domain
 * port. A Failed Result means the panel itself broke (network down,
 * unparseable body); the walk's own verdicts arrive as DATA, not as
 * failures.
 */
export class ReliabilityBreakerRepositoryImpl implements ReliabilityBreakerRepository {
  private readonly api: ReliabilityBreakerApi;

  constructor(api: ReliabilityBreakerApi) {
    this.api = api;
  }

  panel(): Promise<Result<BreakerPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
