import type { Result } from '../../core/result';
import type { RedisPlaygroundDemo } from './redis-playground';
import type { RedisPlaygroundRepository } from './redis-playground-repository';

/**
 * GetRedisPlaygroundDemoUseCase — fetches the redis topic's playground
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` re-runs the walk — the stage is DEL'd per run
 * and the tag names the key family, so repeats answer identically and
 * fresh tags answer freshly.
 */
export class GetRedisPlaygroundDemoUseCase {
  private readonly repository: RedisPlaygroundRepository;

  constructor(repository: RedisPlaygroundRepository) {
    this.repository = repository;
  }

  /** Run the scripted playground with the given tag (default: demo). */
  run(tag: string): Promise<Result<RedisPlaygroundDemo>> {
    return this.repository.playground(tag);
  }
}
