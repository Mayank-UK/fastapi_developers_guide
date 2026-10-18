/**
 * Domain models for the sqlalchemy-orm topic's probe (demo block id
 * `db:orm-probe`) — the client-side shape of GET /api/demo/db/orm-probe.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * One payload carries the whole topic's evidence: the three loading
 * strategies with their MEASURED statement counts, the identity-map
 * proof (two gets → one SELECT, same object), and the dirty-checking
 * proof (one mutated field → exactly one UPDATE, rolled back).
 */

/** One loading strategy's measured run: SQL count, statements, timing. */
export interface StrategyCard {
  strategy: string;
  sqlCount: number;
  statements: string[];
  elapsedMs: number;
  authorCount: number;
  commentTotal: number;
}

/** The identity-map proof: two gets, ONE select, one Python object. */
export interface IdentityMapProof {
  postId: number;
  selectCount: number;
  sameObject: boolean;
  statements: string[];
}

/** The dirty-checking proof: one field, one UPDATE, rolled back. */
export interface DirtyCheckProof {
  postId: number;
  field: string;
  before: string;
  after: string;
  updateCount: number;
  updateSql: string;
  committed: boolean;
}

/** The whole ORM probe payload: strategies + both session proofs. */
export interface OrmProbeDemo {
  postCount: number;
  firstPostTitle: string;
  strategies: StrategyCard[];
  resultsMatch: boolean;
  identityMap: IdentityMapProof;
  dirtyCheck: DirtyCheckProof;
  reasoning: string;
}
