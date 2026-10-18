import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { OrmProbeDemo } from '../../domain/demo/db-orm-probe';
import type { DbOrmProbeRepository } from '../../domain/demo/db-orm-probe-repository';
import type { DbOrmProbeApi } from './db-orm-probe-api';

/**
 * DbOrmProbeRepositoryImpl — adapts the ORM probe API to the domain
 * port. Every thrown transport error is guarded by safeRepositoryCall
 * into a Failed Result.
 */
export class DbOrmProbeRepositoryImpl implements DbOrmProbeRepository {
  private readonly api: DbOrmProbeApi;

  constructor(api: DbOrmProbeApi) {
    this.api = api;
  }

  probe(): Promise<Result<OrmProbeDemo>> {
    return safeRepositoryCall(() => this.api.probe());
  }
}
