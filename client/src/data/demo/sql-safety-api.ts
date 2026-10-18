import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { SqlSafety } from '../../domain/demo/sql-safety';
import { sqlSafetyFromJson } from './sql-safety-dto';

/**
 * SqlSafetyApi — the transport for GET /api/demo/db/sql-safety: the
 * two-way filter probe, with the caller's filter text URL-encoded so
 * any input (quotes, semicolons, comment markers) survives as data.
 * Through the shared guarded fetch pipeline: transport failures and
 * non-2xx envelopes (the 503 for unreachable PostgreSQL) become typed
 * server failures for the error panel.
 */

const SAFETY_PATH = '/demo/db/sql-safety';

export class SqlSafetyApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/sql-safety — executed safety vs rendered danger. */
  async probe(filter?: string): Promise<SqlSafety> {
    const query = filter === undefined ? '' : `?filter=${encodeURIComponent(filter)}`;
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, `${SAFETY_PATH}${query}`);
      return parseDto(body, status, sqlSafetyFromJson);
    });
  }
}
