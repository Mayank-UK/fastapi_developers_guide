import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { SqlLab } from '../../domain/demo/sql-lab';
import { sqlLabFromJson } from './sql-lab-dto';

/**
 * SqlLabApi — the transport for GET /api/demo/db/sql-lab: one exhibit
 * executed for real (ranked · window · thread), selected via the
 * `exhibit` query parameter (encoded; an unknown exhibit answers the
 * 422 envelope through the shared guarded pipeline).
 */

const LAB_PATH = '/demo/db/sql-lab';

export class SqlLabApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/sql-lab — one exhibit's SQL and rows. */
  async lab(exhibit?: string): Promise<SqlLab> {
    const query = exhibit === undefined ? '' : `?exhibit=${encodeURIComponent(exhibit)}`;
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, `${LAB_PATH}${query}`);
      return parseDto(body, status, sqlLabFromJson);
    });
  }
}
