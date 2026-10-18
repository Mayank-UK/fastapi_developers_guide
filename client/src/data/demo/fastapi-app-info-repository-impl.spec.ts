import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { FastApiAppInfoApi } from './fastapi-app-info-api';
import { FastApiAppInfoRepositoryImpl } from './fastapi-app-info-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * FastApiAppInfoRepositoryImpl spec — fixture-driven (happy + failure): the
 * introspection payload round-trips into the domain shape (including the
 * optional docs mounts); network / envelope / malformed-payload failures
 * all resolve as Failed Results, never throws.
 */

const DEMO_URL = '/api/demo/fastapi/app-info';

const appInfoPayload = {
  title: 'FastAPI Developers Guide',
  version: '0.1.0',
  environment: 'dev',
  docs: { docsUrl: '/docs', redocUrl: '/redoc', openapiUrl: '/openapi.json' },
  stack: { fastapi: '0.143.1', starlette: '1.8.0', pydantic: '2.14.1' },
  middleware: ['RequestIdMiddleware'],
  exceptionHandlers: [{ exception: 'AppError', handler: 'handle_app_error' }],
  routes: [
    { path: '/api/health', methods: ['GET'], tags: ['health'] },
    { path: '/api/demo/scenario', methods: ['GET', 'PATCH'], tags: ['demo'] },
  ],
};

function makeRepository(): FastApiAppInfoRepositoryImpl {
  return new FastApiAppInfoRepositoryImpl(new FastApiAppInfoApi(createAppConfig()));
}

describe('FastApiAppInfoRepositoryImpl', () => {
  it('returns a Success with the validated introspection payload', async () => {
    stubApiFetch([{ url: DEMO_URL, body: appInfoPayload }]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.title).toBe('FastAPI Developers Guide');
      expect(result.value.environment).toBe('dev');
      expect(result.value.docs.docsUrl).toBe('/docs');
      expect(result.value.stack.starlette).toBe('1.8.0');
      expect(result.value.middleware).toEqual(['RequestIdMiddleware']);
      expect(result.value.routes[1]?.methods).toEqual(['GET', 'PATCH']);
    }
  });

  it('keeps omitted docs mounts undefined rather than null (family wire rule)', async () => {
    stubApiFetch([
      {
        url: DEMO_URL,
        body: {
          ...appInfoPayload,
          docs: {}, // an app that disabled every docs mount
        },
      },
    ]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.docs.docsUrl).toBeUndefined();
      expect(result.value.docs.redocUrl).toBeUndefined();
      expect(result.value.docs.openapiUrl).toBeUndefined();
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards an error envelope into a Failed Result with its diagnostics', async () => {
    stubApiFetch([
      {
        url: DEMO_URL,
        status: 503,
        body: { error: { code: 'service_unavailable', message: 'calm down', requestId: 'req-9' } },
      },
    ]);

    const result = await makeRepository().get();

    expect(result).toEqual(
      failed(
        new ServerFailure('calm down', {
          code: 'service_unavailable',
          status: 503,
          requestId: 'req-9',
        }),
      ),
    );
  });

  it('guards a malformed payload into a Failed Result (invalid_response)', async () => {
    stubApiFetch([
      // A non-string method must be rejected by the DTO validator.
      {
        url: DEMO_URL,
        body: { ...appInfoPayload, routes: [{ path: '/x', methods: [42], tags: [] }] },
      },
    ]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
