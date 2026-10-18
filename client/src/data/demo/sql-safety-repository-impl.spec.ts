import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { SqlSafetyApi } from './sql-safety-api';
import { SqlSafetyRepositoryImpl } from './sql-safety-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * SqlSafetyRepositoryImpl spec — fixture-driven: the payload round-trips
 * (both cards, rows), the filter travels URL-encoded as a query
 * parameter, malformed payloads resolve as Failed Results, never throw.
 */

const SAFETY_URL = '/api/demo/db/sql-safety';

const payload = {
  filterValue: "'; DROP TABLE posts; --",
  safe: {
    sql: 'SELECT p.id FROM posts AS p WHERE p.title ILIKE :pattern ORDER BY p.id',
    parameterName: 'pattern',
    parameterValue: "%'; DROP TABLE posts; --%",
    rowCount: 1,
    rows: [{ id: 2, slug: 'status-codes-are-a-contract', title: 'Status codes', status: 'published' }],
    note: 'The value traveled as data.',
  },
  unsafe: {
    template: '…',
    renderedSql: "… ILIKE '%'; DROP TABLE posts; --%' …",
    executed: false,
    why: 'Rendered, never executed.',
  },
  wildcardNote: 'Injection ≠ wildcards.',
  reasoning: 'One input, two meanings.',
};

function makeRepository(): SqlSafetyRepositoryImpl {
  return new SqlSafetyRepositoryImpl(new SqlSafetyApi(createAppConfig()));
}

describe('SqlSafetyRepositoryImpl', () => {
  it('fetches and parses the probe payload', async () => {
    stubApiFetch([{ url: SAFETY_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().probe();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.safe.parameterValue).toBe("%'; DROP TABLE posts; --%");
      expect(result.value.safe.rows[0]?.title).toBe('Status codes');
      expect(result.value.unsafe.executed).toBe(false);
    }
  });

  it('rejects an unsafe card without the executed flag', async () => {
    const poisoned = {
      ...payload,
      unsafe: { ...payload.unsafe, executed: 'no' },
    };
    stubApiFetch([{ url: SAFETY_URL, method: 'GET', body: poisoned }]);

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
