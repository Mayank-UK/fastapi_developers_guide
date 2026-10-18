import type { Result } from '../../core/result';
import type { SqlSafety } from './sql-safety';
import type { SqlSafetyRepository } from './sql-safety-repository';

/**
 * GetSqlSafetyDemoUseCase — fetches the databases-sql topic's safety
 * probe (react-guide use-case style): a thin orchestration seam over
 * the repository port. `run` re-fetches with caller filter text so the
 * demo can replay any input through both query constructions.
 */
export class GetSqlSafetyDemoUseCase {
  private readonly repository: SqlSafetyRepository;

  constructor(repository: SqlSafetyRepository) {
    this.repository = repository;
  }

  /** The probe: executed safety vs rendered danger, one input. */
  run(filter?: string): Promise<Result<SqlSafety>> {
    return this.repository.probe(filter);
  }
}
