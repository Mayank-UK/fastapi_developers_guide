import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { RaceDemo } from '../../domain/demo/db-race';
import type { DbRaceRepository } from '../../domain/demo/db-race-repository';
import type { DbRaceApi } from './db-race-api';

/**
 * DbRaceRepositoryImpl — adapts the race API to the domain port. Every
 * thrown transport error is guarded by safeRepositoryCall into a Failed
 * Result.
 */
export class DbRaceRepositoryImpl implements DbRaceRepository {
  private readonly api: DbRaceApi;

  constructor(api: DbRaceApi) {
    this.api = api;
  }

  race(): Promise<Result<RaceDemo>> {
    return safeRepositoryCall(() => this.api.race());
  }
}
