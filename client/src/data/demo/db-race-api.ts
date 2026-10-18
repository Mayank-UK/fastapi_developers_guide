import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { RaceDemo } from '../../domain/demo/db-race';
import { dbRaceFromJson } from './db-race-dto';

/**
 * DbRaceApi — the transport for GET /api/demo/db/race: the two
 * choreographies (unlocked lost update, locked serialization) run
 * server-side deterministically. Through the shared guarded pipeline.
 */

const RACE_PATH = '/demo/db/race';

export class DbRaceApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/race — both final states with verdicts. */
  async race(): Promise<RaceDemo> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, RACE_PATH);
      return parseDto(body, status, dbRaceFromJson);
    });
  }
}
