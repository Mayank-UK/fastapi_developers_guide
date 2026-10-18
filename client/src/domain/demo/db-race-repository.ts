import type { Result } from '../../core/result';
import type { RaceDemo } from './db-race';

/**
 * DbRaceRepository — the domain-facing port for the databases-sql
 * topic's race lab demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. One method, one endpoint: run both choreographies (idempotent;
 * the demo resets and cleans its rows).
 */
export interface DbRaceRepository {
  /** Race the two transactions and return both final states. */
  race(): Promise<Result<RaceDemo>>;
}
