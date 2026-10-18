import type { Result } from '../../core/result';
import type {
  CachingLabDemo,
  ConditionalRound,
  InvalidationOutcome,
  StampedeOutcome,
} from './caching-lab';
import type { CachingLabRepository } from './caching-lab-repository';

/**
 * GetCachingLabDemoUseCase — the caching topic's lab (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * Each action is repeatable — the lab state is the real cache's, so a
 * fetch after an invalidate misses, a fetch after a fill hits, and a
 * stampede always cold-starts before collapsing to one origin fetch.
 */
export class GetCachingLabDemoUseCase {
  private readonly repository: CachingLabRepository;

  constructor(repository: CachingLabRepository) {
    this.repository = repository;
  }

  /** The state panel's roster: key, TTL, cost label, endpoints, state. */
  lab(): Promise<Result<CachingLabDemo>> {
    return this.repository.lab();
  }

  /** One conditional round against the real endpoint (200 or 304). */
  conditionalRound(ifNoneMatch?: string): Promise<Result<ConditionalRound>> {
    return this.repository.conditionalRound(ifNoneMatch);
  }

  /** Explicit invalidation: delete the entry, report the refill ahead. */
  invalidate(): Promise<Result<InvalidationOutcome>> {
    return this.repository.invalidate();
  }

  /** The stampede: N concurrent cold reads, single-flight's counts. */
  stampede(requests: number): Promise<Result<StampedeOutcome>> {
    return this.repository.stampede(requests);
  }
}
