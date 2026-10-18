import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { SearchDemo } from '../../domain/demo/db-search';
import { dbSearchFromJson } from './db-search-dto';

/**
 * DbSearchApi — the transport for GET /api/demo/db/search: ranked
 * full-text matches for a query (URL-encoded; any text dissolves into
 * lexemes server-side, so free input is welcome). Through the shared
 * guarded fetch pipeline.
 */

const SEARCH_PATH = '/demo/db/search';

export class DbSearchApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/search — ranked matches + both plans. */
  async search(q?: string): Promise<SearchDemo> {
    const query = q === undefined ? '' : `?q=${encodeURIComponent(q)}`;
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, `${SEARCH_PATH}${query}`);
      return parseDto(body, status, dbSearchFromJson);
    });
  }
}
