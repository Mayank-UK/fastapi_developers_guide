import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { AuditDemo } from '../../domain/demo/db-audit';
import { dbAuditFromJson } from './db-audit-dto';

/**
 * DbAuditApi — the transport for GET /api/demo/db/audit: both halves of
 * the in-transaction audit proof, run live server-side. Through the
 * shared guarded fetch pipeline.
 */

const AUDIT_PATH = '/demo/db/audit';

export class DbAuditApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/audit — commit-with-row, rollback-without. */
  async prove(): Promise<AuditDemo> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, AUDIT_PATH);
      return parseDto(body, status, dbAuditFromJson);
    });
  }
}
