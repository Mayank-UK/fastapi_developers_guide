import type { Result } from '../../core/result';
import type { SchemaExplorer } from './schema-explorer';

/**
 * SchemaExplorerRepository — the domain-facing port for the sql-schema
 * topic's explorer demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. One method, one endpoint: fetch the live schema roster, or —
 * with a table name — drill into that table's full anatomy (the server
 * answers the honest 404 envelope for an unknown table, which arrives
 * here as a Failed Result like every other non-2xx).
 */
export interface SchemaExplorerRepository {
  /** Fetch the live schema; `table` adds the drill-down focus. */
  explorer(table?: string): Promise<Result<SchemaExplorer>>;
}
