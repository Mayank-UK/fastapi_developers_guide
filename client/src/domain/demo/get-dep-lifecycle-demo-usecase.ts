import type { Result } from '../../core/result';
import type {
  DepLifecycleLogData,
  DepLifecycleSpanData,
} from './dep-lifecycle';
import type { DepLifecycleRepository } from './dep-lifecycle-repository';

/**
 * GetDepLifecycleDemoUseCase — the dependency topic's yield-dependency demo
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. Carries the interactive half too: the user fires a
 * wrapped request, then reads the shared log where that request's teardown
 * landed after the fact.
 */
export class GetDepLifecycleDemoUseCase {
  private readonly repository: DepLifecycleRepository;

  constructor(repository: DepLifecycleRepository) {
    this.repository = repository;
  }

  fire(): Promise<Result<DepLifecycleSpanData>> {
    return this.repository.fire();
  }

  log(): Promise<Result<DepLifecycleLogData>> {
    return this.repository.log();
  }
}
