import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DbSearchApi } from './db-search-api';
import { DbSearchRepositoryImpl } from './db-search-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * DbSearchRepositoryImpl spec — fixture-driven: the search payload
 * round-trips (parsed query, ranked matches, both plans), a query rides
 * URL-encoded, malformed payloads resolve as Failed Results.
 */

const SEARCH_URL = '/api/demo/db/search';
const QUERY_URL = '/api/demo/db/search?q=errors';

const payload = {
  query: 'error envelope',
  parsedQuery: "'error' & 'envelop'",
  sql: 'SELECT …',
  matchCount: 1,
  matches: [
    {
      id: 7,
      slug: 'the-envelope-is-the-error-model',
      title: 'The envelope is the error model',
      rank: 0.10472721606492996,
      headline: 'The <b>envelope</b> is the <b>error</b> model',
    },
  ],
  indexedPlan: ['Bitmap Index Scan on ix_posts_search_vector'],
  naivePlan: ['Seq Scan on posts p'],
  planNote: 'Disclosed: SET LOCAL enable_seqscan = off.',
  reasoning: 'Stems and ranks.',
};

function makeRepository(): DbSearchRepositoryImpl {
  return new DbSearchRepositoryImpl(new DbSearchApi(createAppConfig()));
}

describe('DbSearchRepositoryImpl', () => {
  it('fetches and parses the ranked payload with both plans', async () => {
    stubApiFetch([{ url: SEARCH_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().search();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.parsedQuery).toBe("'error' & 'envelop'");
      expect(result.value.matches[0]?.rank).toBeCloseTo(0.104727, 6);
      expect(result.value.indexedPlan[0]).toContain('ix_posts_search_vector');
      expect(result.value.naivePlan[0]).toContain('Seq Scan');
    }
  });

  it('passes the query through as an encoded query parameter', async () => {
    stubApiFetch([{ url: QUERY_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().search('errors');

    expect(result.ok).toBe(true);
  });

  it('rejects a payload whose plan lines are not strings', async () => {
    const poisoned = { ...payload, indexedPlan: [42] };
    stubApiFetch([{ url: SEARCH_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().search();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().search();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
