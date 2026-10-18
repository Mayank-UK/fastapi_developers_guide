import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { MigrationsDemo } from '../../domain/demo/db-migrations';
import { dbMigrationsFromJson } from './db-migrations-dto';

/**
 * DbMigrationsApi — the transport for GET /api/demo/db/migrations: the
 * two-part rehearsal (failing sequence rolled back atomically, fixed
 * sequence committed). Through the shared guarded fetch pipeline.
 */

const MIGRATIONS_PATH = '/demo/db/migrations';

export class DbMigrationsApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/migrations — rollback proof + commit proof. */
  async rehearse(): Promise<MigrationsDemo> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, MIGRATIONS_PATH);
      return parseDto(body, status, dbMigrationsFromJson);
    });
  }
}
