import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { SqlLabApi } from './sql-lab-api';
import { SqlLabRepositoryImpl } from './sql-lab-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * SqlLabRepositoryImpl spec — fixture-driven: the exhibit answer
 * round-trips (columns, string-cell rows), the exhibit rides URL-encoded
 * as a query parameter, malformed payloads resolve as Failed Results.
 */

const LAB_URL = '/api/demo/db/sql-lab';
const THREAD_URL = '/api/demo/db/sql-lab?exhibit=thread';

const payload = {
  exhibit: 'thread',
  exhibits: [{ id: 'thread', name: 'Recursive CTE', teaches: 'Hop by hop.' }],
  sql: 'WITH RECURSIVE thread AS (…)',
  columns: ['depth', 'author'],
  rows: [{ depth: '1', author: 'maya' }],
  rowCount: 1,
  reading: 'depth counts hops.',
  reasoning: 'Real execution.',
};

function makeRepository(): SqlLabRepositoryImpl {
  return new SqlLabRepositoryImpl(new SqlLabApi(createAppConfig()));
}

describe('SqlLabRepositoryImpl', () => {
  it('fetches and parses the exhibit answer', async () => {
    stubApiFetch([{ url: LAB_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().lab();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.exhibit).toBe('thread');
      expect(result.value.rows[0]?.depth).toBe('1');
      expect(result.value.rowCount).toBe(1);
    }
  });

  it('passes the exhibit through as an encoded query parameter', async () => {
    stubApiFetch([{ url: THREAD_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().lab('thread');

    expect(result.ok).toBe(true);
  });

  it('rejects a row whose cell is not a string', async () => {
    const poisoned = { ...payload, rows: [{ depth: 1, author: 'maya' }] };
    stubApiFetch([{ url: LAB_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().lab();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().lab();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
