import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { AuditDemo } from '../../domain/demo/db-audit';
import type { DbAuditRepository } from '../../domain/demo/db-audit-repository';
import type { DbAuditApi } from './db-audit-api';

/**
 * DbAuditRepositoryImpl — adapts the audit API to the domain port.
 * Every thrown transport error is guarded by safeRepositoryCall into a
 * Failed Result.
 */
export class DbAuditRepositoryImpl implements DbAuditRepository {
  private readonly api: DbAuditApi;

  constructor(api: DbAuditApi) {
    this.api = api;
  }

  prove(): Promise<Result<AuditDemo>> {
    return safeRepositoryCall(() => this.api.prove());
  }
}
