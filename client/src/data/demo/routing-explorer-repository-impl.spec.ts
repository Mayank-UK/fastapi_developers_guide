import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { RoutingExplorerApi } from './routing-explorer-api';
import { RoutingExplorerRepositoryImpl } from './routing-explorer-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * RoutingExplorerRepositoryImpl spec — fixture-driven (happy + failure): the
 * explorer payload round-trips into the domain shape (outcome-conditional
 * fields omitted-when-absent, always-present param arrays); network /
 * envelope / malformed-payload failures all resolve as Failed Results,
 * never throws.
 */

const DEMO_URL =
  '/api/demo/routing/explorer?method=GET&path=%2Fapi%2Fcontent%2Frouting%3Fdeep%3D1';

const matchedPayload = {
  request: { method: 'GET', path: '/api/content/routing' },
  routeCount: 15,
  outcome: 'matched',
  reasoning:
    "GET /api/content/routing matched the declared template /api/content/{topic_id}.",
  matchedPath: '/api/content/{topic_id}',
  matchedMethods: ['GET'],
  matchedTags: ['content'],
  pathParams: [{ name: 'topic_id', value: 'routing', source: 'path' }],
  queryParams: [{ name: 'deep', value: '1', source: 'query' }],
};

function makeRepository(): RoutingExplorerRepositoryImpl {
  return new RoutingExplorerRepositoryImpl(new RoutingExplorerApi(createAppConfig()));
}

describe('RoutingExplorerRepositoryImpl', () => {
  it('returns a Success with the validated match payload', async () => {
    stubApiFetch([{ url: DEMO_URL, body: matchedPayload }]);

    const result = await makeRepository().resolve({
      method: 'GET',
      path: '/api/content/routing?deep=1',
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.outcome).toBe('matched');
      expect(result.value.matchedPath).toBe('/api/content/{topic_id}');
      expect(result.value.pathParams[0]).toEqual({
        name: 'topic_id',
        value: 'routing',
        source: 'path',
      });
      expect(result.value.queryParams[0]?.source).toBe('query');
    }
  });

  it('keeps outcome-conditional fields undefined rather than null (family wire rule)', async () => {
    stubApiFetch([
      {
        url:
          '/api/demo/routing/explorer?method=GET&path=%2Fapi%2Fnope',
        body: {
          request: { method: 'GET', path: '/api/nope' },
          routeCount: 15,
          outcome: 'not_found',
          reasoning: 'matched none of the 15 declared route templates.',
          pathParams: [],
          queryParams: [],
          nearMisses: [{ path: '/api/content', methods: ['GET'] }],
        },
      },
    ]);

    const result = await makeRepository().resolve({ method: 'GET', path: '/api/nope' });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.matchedPath).toBeUndefined();
      expect(result.value.allowedMethods).toBeUndefined();
      expect(result.value.pathParams).toEqual([]);
      expect(result.value.nearMisses?.[0]?.path).toBe('/api/content');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().resolve({ method: 'GET', path: '/api/health' });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards an error envelope into a Failed Result with its diagnostics', async () => {
    stubApiFetch([
      {
        url:
          '/api/demo/routing/explorer?method=GET&path=%2Fapi%2Fhealth',
        status: 503,
        body: { error: { code: 'service_unavailable', message: 'calm down', requestId: 'req-4' } },
      },
    ]);

    const result = await makeRepository().resolve({ method: 'GET', path: '/api/health' });

    expect(result).toEqual(
      failed(
        new ServerFailure('calm down', {
          code: 'service_unavailable',
          status: 503,
          requestId: 'req-4',
        }),
      ),
    );
  });

  it('guards a malformed payload into a Failed Result (invalid_response)', async () => {
    stubApiFetch([
      {
        url: DEMO_URL,
        body: { ...matchedPayload, outcome: 'maybe' }, // not in the closed set
      },
    ]);

    const result = await makeRepository().resolve({
      method: 'GET',
      path: '/api/content/routing?deep=1',
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
