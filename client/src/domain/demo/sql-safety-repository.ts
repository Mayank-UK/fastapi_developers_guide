import type { Result } from '../../core/result';
import type { SqlSafety } from './sql-safety';

/**
 * SqlSafetyRepository — the domain-facing port for the databases-sql
 * topic's safety probe demo. Demo components depend on this interface
 * only; the HTTP adapter lives in data/demo and is wired at the
 * composition root. One method, one endpoint: run the filter probe with
 * the caller's (optional) filter text.
 */
export interface SqlSafetyRepository {
  /** Run the probe; `filter` defaults to the canonical injection payload. */
  probe(filter?: string): Promise<Result<SqlSafety>>;
}
