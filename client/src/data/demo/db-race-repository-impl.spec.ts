import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DbRaceApi } from './db-race-api';
import { DbRaceRepositoryImpl } from './db-race-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * DbRaceRepositoryImpl spec — fixture-driven: both runs round-trip
 * (timelines, final slots, verdicts), malformed payloads resolve as
 * Failed Results, never throw.
 */

const RACE_URL = '/api/demo/db/race';

const payload = {
  postId: 1,
  postTitle: 'Designing URLs people can read',
  baselineComments: 2,
  unlocked: {
    mode: 'read-modify-write',
    timeline: ['A reads COUNT(*) = 2'],
    finalSlots: [{ author: 'race-runner-a', body: 'slot #3 (unlocked run)' }],
    verdict: 'LOST UPDATE.',
  },
  locked: {
    mode: 'select-for-update',
    timeline: ['B requests the lock and BLOCKS'],
    finalSlots: [{ author: 'race-runner-b', body: 'slot #4 (locked run)' }],
    verdict: 'SERIALIZED.',
  },
  reasoning: 'The lock is the difference.',
};

function makeRepository(): DbRaceRepositoryImpl {
  return new DbRaceRepositoryImpl(new DbRaceApi(createAppConfig()));
}

describe('DbRaceRepositoryImpl', () => {
  it('fetches and parses both runs with their verdicts', async () => {
    stubApiFetch([{ url: RACE_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().race();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.baselineComments).toBe(2);
      expect(result.value.unlocked.finalSlots[0]?.author).toBe('race-runner-a');
      expect(result.value.locked.verdict).toBe('SERIALIZED.');
    }
  });

  it('rejects a payload whose timeline entry is not a string', async () => {
    const poisoned = {
      ...payload,
      locked: { ...payload.locked, timeline: [17] },
    };
    stubApiFetch([{ url: RACE_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().race();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().race();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
