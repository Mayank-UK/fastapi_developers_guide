import type { Result } from '../../core/result';
import type { RaceDemo } from './db-race';
import type { DbRaceRepository } from './db-race-repository';

/**
 * GetDbRaceDemoUseCase — fetches the databases-sql topic's race lab
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` re-runs the race — deterministically, so
 * repeated runs answer identically.
 */
export class GetDbRaceDemoUseCase {
  private readonly repository: DbRaceRepository;

  constructor(repository: DbRaceRepository) {
    this.repository = repository;
  }

  /** Race unlocked vs locked, once. */
  run(): Promise<Result<RaceDemo>> {
    return this.repository.race();
  }
}
