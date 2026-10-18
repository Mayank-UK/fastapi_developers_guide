import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure, type StubRoute } from '../../test/fetch_stub';
import { CachingLabApi } from './caching-lab-api';
import { CachingLabRepositoryImpl } from './caching-lab-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * CachingLabRepositoryImpl spec — fixture-driven: the roster, invalidate,
 * and stampede payloads round-trip as Ok Results; the RAW conditional
 * round reports both of its honest answers (a 200 with body bytes and a
 * bodyless 304 with the same validators); transport failures and error
 * envelopes resolve as Failed Results, never throw.
 */

const labRoute: StubRoute = {
  url: '/api/demo/caching/lab',
  body: {
    namespace: 'guide_demo:caching:*',
    key: 'guide_demo:caching:posts:v1',
    ttlSeconds: 2,
    originCostMs: 120,
    originCostNote: 'simulated — the real substrate answers in microseconds',
    postsEndpoint: '/api/demo/caching/posts',
    invalidateEndpoint: '/api/demo/caching/invalidate',
    stampedeEndpoint: '/api/demo/caching/stampede',
    state: {
      key: 'guide_demo:caching:posts:v1',
      present: true,
      ttlSeconds: 2,
      ttlRemainingS: 1,
      sizeBytes: 512,
      etag: '"abc0123456789def"',
      lastOutcome: 'hit',
      telemetry: { hits: 3, misses: 1, coalesced: 2, invalidations: 1 },
    },
    reasoning: 'One key caches the newest-posts page as its canonical JSON string.',
  },
};

const conditionalHeaders = {
  etag: '"abc0123456789def"',
  'cache-control': 'no-cache',
  'x-cache': 'hit',
  'x-cache-elapsed-ms': '2',
  'x-cache-age-ms': '1000',
  'x-cache-origin-fetches': '1',
  'x-cache-hits': '5',
};

function conditionalRoute(status: 200 | 304): StubRoute {
  return {
    url: '/api/demo/caching/posts',
    method: 'GET',
    status,
    headers: conditionalHeaders,
    ...(status === 200 ? { body: { items: [], total: 0, page: 1, limit: 6, pages: 0 } } : {}),
  };
}

function makeRepository(): CachingLabRepositoryImpl {
  const config = createAppConfig();
  return new CachingLabRepositoryImpl(new CachingLabApi(config));
}

describe('CachingLabRepositoryImpl', () => {
  it('round-trips the lab roster payload', async () => {
    stubApiFetch([labRoute]);
    const result = await makeRepository().lab();
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.key).toBe('guide_demo:caching:posts:v1');
    expect(result.value.state.telemetry).toEqual({
      hits: 3,
      misses: 1,
      coalesced: 2,
      invalidations: 1,
    });
    expect(result.value.state.ttlRemainingS).toBe(1);
  });

  it('round-trips invalidation and stampede outcomes', async () => {
    stubApiFetch([
      {
        url: '/api/demo/caching/invalidate',
        method: 'POST',
        body: {
          key: 'guide_demo:caching:posts:v1',
          deletedEntries: 1,
          telemetry: { hits: 3, misses: 1, coalesced: 2, invalidations: 1 },
          detail: 'deleted 1 entry — the next read is a miss',
        },
      },
      {
        url: '/api/demo/caching/stampede',
        method: 'POST',
        body: {
          requests: 8,
          originFetches: 1,
          servedWarm: 7,
          wallMs: 131,
          rounds: [
            { index: 0, outcome: 'miss', elapsedMs: 128 },
            { index: 1, outcome: 'coalesced', elapsedMs: 129 },
          ],
          proof: 'exactly 1 origin fetch',
        },
      },
    ]);
    const repository = makeRepository();

    const invalidated = await repository.invalidate();
    expect(invalidated.ok && invalidated.value.deletedEntries).toBe(1);

    const stampede = await repository.stampede(8);
    expect(stampede.ok && stampede.value.originFetches).toBe(1);
    expect(stampede.ok && stampede.value.rounds[1]?.outcome).toBe('coalesced');
  });

  it('reports a 200 conditional round with its body bytes', async () => {
    stubApiFetch([conditionalRoute(200)]);
    const result = await makeRepository().conditionalRound();
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.status).toBe(200);
    expect(result.value.cache).toBe('hit');
    expect(result.value.ageMs).toBe(1000);
    expect(result.value.bodyBytes).toBeGreaterThan(0);
  });

  it('reports the bodyless 304 with the same validators', async () => {
    stubApiFetch([conditionalRoute(304)]);
    const result = await makeRepository().conditionalRound('"abc0123456789def"');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.status).toBe(304);
    expect(result.value.etag).toBe('"abc0123456789def"');
    expect(result.value.bodyBytes).toBe(0);
  });

  it('resolves the 503 error envelope as a Failed Result, never throws', async () => {
    stubApiFetch([
      {
        url: '/api/demo/caching/lab',
        status: 503,
        body: {
          error: {
            code: 'service_unavailable',
            message: 'Redis is unreachable.',
            requestId: 'req-c1',
          },
        },
      },
    ]);
    const result = await makeRepository().lab();
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.failure.message).toBe('Redis is unreachable.');
  });

  it('resolves network failures as Failed Results', async () => {
    stubNetworkFailure();
    const result = await makeRepository().lab();
    expect(result.ok).toBe(false);
  });
});
