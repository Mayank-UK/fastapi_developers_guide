/**
 * Domain models for the databases-sql topic's migration rehearsal
 * (demo block id `db:migrations`) — the client-side shape of
 * GET /api/demo/db/migrations. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * Two runs over one scratch table: `failing` applies two steps then
 * PostgreSQL refuses the third — and transactional DDL rolls the whole
 * sequence back (verified: the table does not exist); `succeeding`
 * applies the fixed sequence and commits (verified: one row). Every
 * step's SQL and outcome rides in the payload.
 */

/** One rehearsed step: description, SQL, and what became of it. */
export interface MigrationStep {
  description: string;
  sql: string;
  outcome: string;
}

/** One full rehearsal: steps, ending, verification read after. */
export interface MigrationRun {
  scenario: string;
  scratchTable: string;
  steps: MigrationStep[];
  /** The real PostgreSQL error text; absent when the run committed. */
  failure?: string;
  committed: boolean;
  tableExistsAfter: boolean;
  rowCountAfter?: number;
}

/** The whole rehearsal payload: both runs + the cleanup honesty note. */
export interface MigrationsDemo {
  scratchTable: string;
  failing: MigrationRun;
  succeeding: MigrationRun;
  cleanupNote: string;
  reasoning: string;
}
