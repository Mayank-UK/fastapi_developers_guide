import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { SearchDemo } from '../../domain/demo/db-search';
import type { DbSearchRepository } from '../../domain/demo/db-search-repository';
import type { DbSearchApi } from './db-search-api';

/**
 * DbSearchRepositoryImpl — adapts the search API to the domain port.
 * Every thrown transport error is guarded by safeRepositoryCall into a
 * Failed Result.
 */
export class DbSearchRepositoryImpl implements DbSearchRepository {
  private readonly api: DbSearchApi;

  constructor(api: DbSearchApi) {
    this.api = api;
  }

  search(q?: string): Promise<Result<SearchDemo>> {
    return safeRepositoryCall(() => this.api.search(q));
  }
}
