import type { Result } from '../../core/result';
import type { MongoConsoleDemo } from './mongo-console';
import type { MongoConsoleRepository } from './mongo-console-repository';

/**
 * GetMongoConsoleDemoUseCase — fetches the mongodb topic's console
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` re-runs the console — the seed is keyed and
 * the demo document cleans up after itself, so repeats answer
 * identically.
 */
export class GetMongoConsoleDemoUseCase {
  private readonly repository: MongoConsoleRepository;

  constructor(repository: MongoConsoleRepository) {
    this.repository = repository;
  }

  /** Run the scripted console with the given find tag (default: indexes). */
  run(tag: string): Promise<Result<MongoConsoleDemo>> {
    return this.repository.console(tag);
  }
}
