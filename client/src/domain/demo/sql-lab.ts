/**
 * Domain models for the databases-sql topic's SQL lab (demo block id
 * `db:sql-lab`) — the client-side shape of
 * GET /api/demo/db/sql-lab?exhibit=. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * Three hand-written exhibits, each executed for real over the seeded
 * posts and comments: `ranked` (per-author ROW_NUMBER + global RANK),
 * `window` (running total and average across the timeline), `thread`
 * (a recursive CTE walking one post's comment thread). The payload
 * carries the chosen exhibit's verbatim SQL, columns, and rows.
 */

/** One exhibit as the picker lists it. */
export interface ExhibitCard {
  id: string;
  name: string;
  teaches: string;
}

/** One exhibit's answer: SQL, columns, display-formatted rows. */
export interface SqlLab {
  exhibit: string;
  exhibits: ExhibitCard[];
  sql: string;
  columns: string[];
  rows: Record<string, string>[];
  rowCount: number;
  reading: string;
  reasoning: string;
}
