import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { OrmProbeDemo } from '../../domain/demo/db-orm-probe';
import { dbOrmProbeFromJson } from './db-orm-probe-dto';

/**
 * DbOrmProbeApi — the transport for GET /api/demo/db/orm-probe: the
 * three loading strategies (lazy, joinedload, selectinload) measured
 * with real query counting, plus the identity-map and dirty-checking
 * proofs. Through the shared guarded pipeline.
 */

const ORM_PROBE_PATH = '/demo/db/orm-probe';

export class DbOrmProbeApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/orm-probe — strategies + session proofs. */
  async probe(): Promise<OrmProbeDemo> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, ORM_PROBE_PATH);
      return parseDto(body, status, dbOrmProbeFromJson);
    });
  }
}
