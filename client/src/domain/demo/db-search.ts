/**
 * Domain models for the databases-sql topic's search lab (demo block id
 * `db:search`) — the client-side shape of GET /api/demo/db/search?q=.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * Ranked full-text search over the 0002 generated tsvector column: the
 * parsed (stemmed) tsquery, matches ordered by ts_rank with highlighted
 * headlines, and BOTH EXPLAIN plans captured live — the GIN bitmap scan
 * vs the no-index seq scan that recomputes the vector per row.
 */

/** One ranked hit with its highlighted match context. */
export interface SearchMatch {
  id: number;
  slug: string;
  title: string;
  rank: number;
  headline: string;
}

/** The whole search payload: parsed query, matches, both plans. */
export interface SearchDemo {
  query: string;
  parsedQuery: string;
  sql: string;
  matchCount: number;
  matches: SearchMatch[];
  indexedPlan: string[];
  naivePlan: string[];
  planNote: string;
  reasoning: string;
}
