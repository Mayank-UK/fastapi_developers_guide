import type { Result } from '../../core/result';
import type { MigrationsDemo } from './db-migrations';
import type { DbMigrationsRepository } from './db-migrations-repository';

/**
 * GetDbMigrationsDemoUseCase — fetches the databases-sql topic's
 * migration rehearsal (react-guide use-case style): a thin orchestration
 * seam over the repository port. `run` re-rehearses (idempotent — the
 * demo drops its scratch table after the proof).
 */
export class GetDbMigrationsDemoUseCase {
  private readonly repository: DbMigrationsRepository;

  constructor(repository: DbMigrationsRepository) {
    this.repository = repository;
  }

  /** The rehearsal: rollback atomicity, then the committed sequence. */
  run(): Promise<Result<MigrationsDemo>> {
    return this.repository.rehearse();
  }
}
