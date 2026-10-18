import type { Result } from '../../core/result';
import type { SqlLab } from './sql-lab';

/**
 * SqlLabRepository — the domain-facing port for the databases-sql
 * topic's SQL lab demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. One method, one endpoint: execute one exhibit (ranked ·
 * window · thread).
 */
export interface SqlLabRepository {
  /** Execute one exhibit; `exhibit` defaults to `ranked`. */
  lab(exhibit?: string): Promise<Result<SqlLab>>;
}
