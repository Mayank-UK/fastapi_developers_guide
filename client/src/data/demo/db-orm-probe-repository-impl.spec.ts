import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DbOrmProbeApi } from './db-orm-probe-api';
import { DbOrmProbeRepositoryImpl } from './db-orm-probe-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * DbOrmProbeRepositoryImpl spec — fixture-driven: the three strategies
 * with their measured counts round-trip, malformed payloads resolve as
 * Failed Results, never throw.
 */

const ORM_PROBE_URL = '/api/demo/db/orm-probe';

const payload = {
  postCount: 5,
  firstPostTitle: 'Designing URLs people can read',
  strategies: [
    {
      strategy: 'lazy',
      sqlCount: 9,
      statements: ['SELECT posts.id FROM posts'],
      elapsedMs: 3.2,
      authorCount: 5,
      commentTotal: 11,
    },
    {
      strategy: 'joinedload',
      sqlCount: 1,
      statements: ['SELECT … LEFT OUTER JOIN'],
      elapsedMs: 1.1,
      authorCount: 5,
      commentTotal: 11,
    },
    {
      strategy: 'selectinload',
      sqlCount: 3,
      statements: ['SELECT …', 'SELECT … IN (…)'],
      elapsedMs: 1.7,
      authorCount: 5,
      commentTotal: 11,
    },
  ],
  resultsMatch: true,
  identityMap: {
    postId: 1,
    selectCount: 1,
    sameObject: true,
    statements: ['SELECT posts.id FROM posts WHERE id = 1'],
  },
  dirtyCheck: {
    postId: 1,
    field: 'status',
    before: 'published',
    after: 'draft',
    updateCount: 1,
    updateSql: 'UPDATE posts SET status=$1 WHERE posts.version = $4',
    committed: false,
  },
  reasoning: 'Measured, not asserted.',
};

function makeRepository(): DbOrmProbeRepositoryImpl {
  return new DbOrmProbeRepositoryImpl(new DbOrmProbeApi(createAppConfig()));
}

describe('DbOrmProbeRepositoryImpl', () => {
  it('fetches and parses the strategies plus both proofs', async () => {
    stubApiFetch([{ url: ORM_PROBE_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().probe();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.strategies).toHaveLength(3);
      expect(result.value.strategies[0]?.sqlCount).toBe(9);
      expect(result.value.identityMap.sameObject).toBe(true);
      expect(result.value.dirtyCheck.committed).toBe(false);
    }
  });

  it('rejects a payload whose strategy statement is not a string', async () => {
    const poisoned = {
      ...payload,
      strategies: [{ ...payload.strategies[0], statements: [17] }],
    };
    stubApiFetch([{ url: ORM_PROBE_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().probe();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().probe();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
