import {
  type DirtyCheckProof,
  type IdentityMapProof,
  type OrmProbeDemo,
  type StrategyCard,
} from '../../domain/demo/db-orm-probe';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * DbOrmProbeDTO — the wire/transport shapes of the ORM probe: the three
 * loading strategies with measured counts, the identity-map proof, and
 * the dirty-checking proof.
 */

export type DbOrmProbeDto = OrmProbeDemo;

function strategyLine(value: unknown, index: number): string {
  if (typeof value !== 'string') {
    throw new Error(`expected statement line at ${index}`);
  }
  return value;
}

function strategyFromJson(body: unknown): StrategyCard {
  if (!isRecord(body)) throw new Error('strategy card must be an object');
  return {
    strategy: requiredString(body, 'strategy'),
    sqlCount: requiredNumber(body, 'sqlCount'),
    statements: requiredArray(body, 'statements').map(strategyLine),
    elapsedMs: requiredNumber(body, 'elapsedMs'),
    authorCount: requiredNumber(body, 'authorCount'),
    commentTotal: requiredNumber(body, 'commentTotal'),
  };
}

function identityMapFromJson(body: unknown): IdentityMapProof {
  if (!isRecord(body)) throw new Error('identity map proof must be an object');
  return {
    postId: requiredNumber(body, 'postId'),
    selectCount: requiredNumber(body, 'selectCount'),
    sameObject: requiredBoolean(body, 'sameObject'),
    statements: requiredArray(body, 'statements').map(strategyLine),
  };
}

function dirtyCheckFromJson(body: unknown): DirtyCheckProof {
  if (!isRecord(body)) throw new Error('dirty check proof must be an object');
  return {
    postId: requiredNumber(body, 'postId'),
    field: requiredString(body, 'field'),
    before: requiredString(body, 'before'),
    after: requiredString(body, 'after'),
    updateCount: requiredNumber(body, 'updateCount'),
    updateSql: requiredString(body, 'updateSql'),
    committed: requiredBoolean(body, 'committed'),
  };
}

/** Deserialize + validate the ORM probe payload (strategies + proofs). */
export function dbOrmProbeFromJson(body: unknown): DbOrmProbeDto {
  if (!isRecord(body)) throw new Error('orm probe demo must be an object');
  return {
    postCount: requiredNumber(body, 'postCount'),
    firstPostTitle: requiredString(body, 'firstPostTitle'),
    strategies: requiredArray(body, 'strategies').map(strategyFromJson),
    resultsMatch: requiredBoolean(body, 'resultsMatch'),
    identityMap: identityMapFromJson(body.identityMap),
    dirtyCheck: dirtyCheckFromJson(body.dirtyCheck),
    reasoning: requiredString(body, 'reasoning'),
  };
}
