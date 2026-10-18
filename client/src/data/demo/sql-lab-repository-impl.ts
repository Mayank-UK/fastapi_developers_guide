import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { SqlLab } from '../../domain/demo/sql-lab';
import type { SqlLabRepository } from '../../domain/demo/sql-lab-repository';
import type { SqlLabApi } from './sql-lab-api';

/**
 * SqlLabRepositoryImpl — adapts the lab API to the domain port. Every
 * thrown transport error is guarded by safeRepositoryCall into a Failed
 * Result.
 */
export class SqlLabRepositoryImpl implements SqlLabRepository {
  private readonly api: SqlLabApi;

  constructor(api: SqlLabApi) {
    this.api = api;
  }

  lab(exhibit?: string): Promise<Result<SqlLab>> {
    return safeRepositoryCall(() => this.api.lab(exhibit));
  }
}
