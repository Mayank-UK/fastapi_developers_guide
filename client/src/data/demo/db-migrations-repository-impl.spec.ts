import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DbMigrationsApi } from './db-migrations-api';
import { DbMigrationsRepositoryImpl } from './db-migrations-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * DbMigrationsRepositoryImpl spec — fixture-driven: both runs round-trip
 * (steps, optional failure/rowCountAfter surface as undefined when
 * absent), malformed payloads resolve as Failed Results, never throw.
 */

const MIGRATIONS_URL = '/api/demo/db/migrations';

const payload = {
  scratchTable: 'migration_lab_scratch',
  failing: {
    scenario: 'failing',
    scratchTable: 'migration_lab_scratch',
    steps: [{ description: 'create', sql: 'CREATE TABLE …', outcome: 'applied' }],
    failure: 'column "size" contains null values',
    committed: false,
    tableExistsAfter: false,
  },
  succeeding: {
    scenario: 'succeeding',
    scratchTable: 'migration_lab_scratch',
    steps: [{ description: 'create', sql: 'CREATE TABLE …', outcome: 'applied' }],
    committed: true,
    tableExistsAfter: true,
    rowCountAfter: 1,
  },
  cleanupNote: 'Dropped again after the proof.',
  reasoning: 'All or nothing.',
};

function makeRepository(): DbMigrationsRepositoryImpl {
  return new DbMigrationsRepositoryImpl(new DbMigrationsApi(createAppConfig()));
}

describe('DbMigrationsRepositoryImpl', () => {
  it('fetches and parses both runs, optionals intact', async () => {
    stubApiFetch([{ url: MIGRATIONS_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().rehearse();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.failing.failure).toBe('column "size" contains null values');
      expect(result.value.failing.rowCountAfter).toBeUndefined();
      expect(result.value.succeeding.failure).toBeUndefined();
      expect(result.value.succeeding.rowCountAfter).toBe(1);
    }
  });

  it('rejects a payload whose committed flag is missing', async () => {
    const poisoned = {
      ...payload,
      succeeding: { ...payload.succeeding, committed: undefined },
    };
    stubApiFetch([{ url: MIGRATIONS_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().rehearse();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().rehearse();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
