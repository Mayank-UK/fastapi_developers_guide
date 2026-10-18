import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { MigrationsDemo } from '../../domain/demo/db-migrations';
import type { DbMigrationsRepository } from '../../domain/demo/db-migrations-repository';
import type { DbMigrationsApi } from './db-migrations-api';

/**
 * DbMigrationsRepositoryImpl — adapts the rehearsal API to the domain
 * port. Every thrown transport error is guarded by safeRepositoryCall
 * into a Failed Result.
 */
export class DbMigrationsRepositoryImpl implements DbMigrationsRepository {
  private readonly api: DbMigrationsApi;

  constructor(api: DbMigrationsApi) {
    this.api = api;
  }

  rehearse(): Promise<Result<MigrationsDemo>> {
    return safeRepositoryCall(() => this.api.rehearse());
  }
}
