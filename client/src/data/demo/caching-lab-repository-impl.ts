import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type {
  CachingLabDemo,
  ConditionalRound,
  InvalidationOutcome,
  StampedeOutcome,
} from '../../domain/demo/caching-lab';
import type { CachingLabRepository } from '../../domain/demo/caching-lab-repository';
import type { CachingLabApi } from './caching-lab-api';

/**
 * CachingLabRepositoryImpl — adapts the caching lab API to the domain
 * port. Every thrown transport error is guarded by safeRepositoryCall
 * into a Failed Result.
 */
export class CachingLabRepositoryImpl implements CachingLabRepository {
  private readonly api: CachingLabApi;

  constructor(api: CachingLabApi) {
    this.api = api;
  }

  lab(): Promise<Result<CachingLabDemo>> {
    return safeRepositoryCall(() => this.api.lab());
  }

  conditionalRound(ifNoneMatch?: string): Promise<Result<ConditionalRound>> {
    return safeRepositoryCall(() => this.api.conditionalRound(ifNoneMatch));
  }

  invalidate(): Promise<Result<InvalidationOutcome>> {
    return safeRepositoryCall(() => this.api.invalidate());
  }

  stampede(requests: number): Promise<Result<StampedeOutcome>> {
    return safeRepositoryCall(() => this.api.stampede(requests));
  }
}
