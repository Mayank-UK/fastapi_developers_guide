/**
 * Domain models for the databases-sql topic's safety probe (demo block
 * id `db:sql-safety`) — the client-side shape of
 * GET /api/demo/db/sql-safety. Field names match the server's camelCase
 * wire contract 1:1.
 *
 * One filter input, two query constructions: `safe` REALLY EXECUTED with
 * the caller's text as a bind parameter (hostile input arrives as data
 * and simply matches fewer rows), `unsafe` the string-interpolated
 * statement rendered as display text — `executed` is false, and the
 * rendered SQL shows exactly how a quote breaks the statement apart.
 */

/** One post as the executed filter returned it. */
export interface PostBrief {
  id: number;
  slug: string;
  title: string;
  status: string;
}

/** The executed parameterized query: SQL, bind value, real rows. */
export interface SafeQuery {
  sql: string;
  parameterName: string;
  parameterValue: string;
  rowCount: number;
  rows: PostBrief[];
  note: string;
}

/** The interpolated twin — rendered, explained, never executed. */
export interface UnsafeQuery {
  template: string;
  renderedSql: string;
  executed: boolean;
  why: string;
}

/** The whole safety payload: both cards, the boundary note, reasoning. */
export interface SqlSafety {
  filterValue: string;
  safe: SafeQuery;
  unsafe: UnsafeQuery;
  wildcardNote: string;
  reasoning: string;
}
