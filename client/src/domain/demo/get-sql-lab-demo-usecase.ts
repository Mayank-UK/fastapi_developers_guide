import type { Result } from '../../core/result';
import type { SqlLab } from './sql-lab';
import type { SqlLabRepository } from './sql-lab-repository';

/**
 * GetSqlLabDemoUseCase — fetches the databases-sql topic's SQL lab
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` executes one exhibit; the roster of available
 * exhibits arrives with every answer.
 */
export class GetSqlLabDemoUseCase {
  private readonly repository: SqlLabRepository;

  constructor(repository: SqlLabRepository) {
    this.repository = repository;
  }

  /** Execute one exhibit (ranked · window · thread). */
  run(exhibit?: string): Promise<Result<SqlLab>> {
    return this.repository.lab(exhibit);
  }
}
