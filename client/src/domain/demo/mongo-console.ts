/**
 * Domain models for the mongodb topic's console (demo block id
 * `db:mongo-console`) — the client-side shape of
 * GET /api/demo/db/mongo-console. Field names match the server's
 * camelCase wire contract 1:1 (document rows inside operations keep
 * the server's snake_case field names — they are display strings).
 *
 * One payload carries the whole scripted console: the idempotent seed,
 * the pydantic refusal at the document boundary, the insert/find/
 * update/count/delete lifecycle, the COLLSCAN-vs-IXSCAN index exhibit,
 * and a real TTL index definition.
 */

/** The seed step: keyed upserts, so repeats are idempotent. */
export interface SeedReport {
  collection: string;
  seedKeys: string[];
  countBefore: number;
  upserted: number;
  totalAfter: number;
  indexesEnsured: string[];
}

/** The boundary's refusal: what was attempted and why it never ran. */
export interface RefusalRow {
  attempted: Record<string, string>;
  errors: string[];
}

/** One console operation and what the live MongoDB answered. */
export interface ConsoleOperationRow {
  op: string;
  description: string;
  command: string;
  outcome: string;
  documents: Record<string, string>[];
}

/** One explain(): the winning plan's access stage with its exam counts. */
export interface ExplainStageRow {
  label: string;
  query: string;
  stage: string;
  indexName?: string;
  keysExamined: number;
  docsExamined: number;
}

/** The index exhibit: one query, explained before and after createIndex. */
export interface IndexShowcaseRow {
  collection: string;
  documentCount: number;
  indexCommand: string;
  explains: ExplainStageRow[];
}

/** The TTL exhibit: a real expireAfterSeconds index, definition shown. */
export interface TtlShowcaseRow {
  collection: string;
  indexDefinition: Record<string, string>;
  expireAfterSeconds: number;
  scratchDocuments: Record<string, string>[];
  evictionNote: string;
}

/** The whole console payload: seed, refusal, lifecycle, both exhibits. */
export interface MongoConsoleDemo {
  database: string;
  seed: SeedReport;
  refusal: RefusalRow;
  operations: ConsoleOperationRow[];
  indexShowcase: IndexShowcaseRow;
  ttlShowcase: TtlShowcaseRow;
  reasoning: string;
}
