import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { SchemaExplorer } from '../../domain/demo/schema-explorer';
import { schemaExplorerFromJson } from './schema-explorer-dto';

/**
 * SchemaExplorerApi — the transport for GET /api/demo/db/schema-explorer:
 * the roster of the LIVE schema, optionally drilled into one table via
 * the `table` query parameter (encoded so any value survives as data).
 * Through the shared guarded fetch pipeline: transport failures and
 * non-2xx envelopes (the honest 404 for an unknown table, the 503 for
 * an unreachable PostgreSQL) become typed server failures for the error
 * panel; a good transport is validated into the DTO.
 */

const EXPLORER_PATH = '/demo/db/schema-explorer';

export class SchemaExplorerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/schema-explorer — the live schema, optionally focused. */
  async explorer(table?: string): Promise<SchemaExplorer> {
    const query = table === undefined ? '' : `?table=${encodeURIComponent(table)}`;
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, `${EXPLORER_PATH}${query}`);
      return parseDto(body, status, schemaExplorerFromJson);
    });
  }
}
