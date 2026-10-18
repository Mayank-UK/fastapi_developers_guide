import type { Result } from '../../core/result';
import type { MigrationsDemo } from './db-migrations';

/**
 * DbMigrationsRepository — the domain-facing port for the databases-sql
 * topic's migration rehearsal demo. Demo components depend on this
 * interface only; the HTTP adapter lives in data/demo and is wired at
 * the composition root. One method, one endpoint: run the rehearsal
 * (failing sequence rolled back, fixed sequence committed).
 */
export interface DbMigrationsRepository {
  /** Run the two-part rehearsal against the live scratch table. */
  rehearse(): Promise<Result<MigrationsDemo>>;
}
