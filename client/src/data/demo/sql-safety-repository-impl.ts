import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { SqlSafety } from '../../domain/demo/sql-safety';
import type { SqlSafetyRepository } from '../../domain/demo/sql-safety-repository';
import type { SqlSafetyApi } from './sql-safety-api';

/**
 * SqlSafetyRepositoryImpl — adapts the safety API to the domain port.
 * Every thrown transport error (network, non-2xx envelope, malformed
 * payload) is guarded by safeRepositoryCall into a Failed Result, so
 * the demo component never needs try/catch.
 */
export class SqlSafetyRepositoryImpl implements SqlSafetyRepository {
  private readonly api: SqlSafetyApi;

  constructor(api: SqlSafetyApi) {
    this.api = api;
  }

  probe(filter?: string): Promise<Result<SqlSafety>> {
    return safeRepositoryCall(() => this.api.probe(filter));
  }
}
