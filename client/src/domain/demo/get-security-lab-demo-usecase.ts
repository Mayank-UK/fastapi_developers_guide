import type { Result } from '../../core/result';
import type { SecurityLabRepository } from './security-lab-repository';
import type { BurnResult, SecurityLabLoad } from './security-lab';

/**
 * GetSecurityLabDemoUseCase — the security lab's use case: the panel with
 * its observed live headers, and the burner over the genuinely throttled
 * endpoint (each burn returns the remaining budget until the dependency
 * raises the 429 with Retry-After — surfaced here as a typed throttle
 * shape, because it is the lesson, not an error).
 */
export class GetSecurityLabDemoUseCase {
  private readonly repository: SecurityLabRepository;

  constructor(repository: SecurityLabRepository) {
    this.repository = repository;
  }

  /** The panel + what the live response actually carried. */
  panel(): Promise<Result<SecurityLabLoad>> {
    return this.repository.panel();
  }

  /** Burn one unit of the real budget; the throttle is a typed outcome. */
  burn(): Promise<Result<BurnResult>> {
    return this.repository.burn();
  }
}
