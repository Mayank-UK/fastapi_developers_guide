import type { Result } from '../../core/result';
import type { SearchDemo } from './db-search';

/**
 * DbSearchRepository — the domain-facing port for the databases-sql
 * topic's search lab demo. Demo components depend on this interface
 * only; the HTTP adapter lives in data/demo and is wired at the
 * composition root. One method, one endpoint: rank full-text matches
 * for a query (the parsed tsquery rides in every payload).
 */
export interface DbSearchRepository {
  /** Search; `q` defaults to the seeded 'error envelope' tour. */
  search(q?: string): Promise<Result<SearchDemo>>;
}
