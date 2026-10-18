import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { ReqresInspectorApi } from './reqres-inspector-api';
import { ReqresInspectorRepositoryImpl } from './reqres-inspector-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * ReqresInspectorRepositoryImpl spec — fixture-driven (happy + failure): the
 * probe's query string and custom header travel on the wire exactly as
 * configured, the reflected payload round-trips into the domain shape
 * (request-conditional fields omitted-when-absent, always-present arrays),
 * and network / envelope / malformed-payload failures resolve as Failed
 * Results, never throws.
 */

const reflectedPayload = {
  method: 'GET',
  path: '/api/demo/reqres/inspector',
  rawQuery: 'tag=a&tag=b',
  queryParams: [{ name: 'tag', values: ['a', 'b'], isRepeated: true }],
  headers: [{ name: 'x-probe', value: 'hello' }],
  requestId: 'req-31',
  requestIdHeader: 'x-request-id',
  reasoning: 'This payload is the handler\'s own view of the GET request.',
};

function makeRepository(): ReqresInspectorRepositoryImpl {
  return new ReqresInspectorRepositoryImpl(new ReqresInspectorApi(createAppConfig()));
}

describe('ReqresInspectorRepositoryImpl', () => {
  it('returns a Success with the validated reflection', async () => {
    stubApiFetch([{ url: '/api/demo/reqres/inspector?tag=a&tag=b', body: reflectedPayload }]);

    const result = await makeRepository().probe({ method: 'GET', query: 'tag=a&tag=b' });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.method).toBe('GET');
      expect(result.value.queryParams[0]).toEqual({
        name: 'tag',
        values: ['a', 'b'],
        isRepeated: true,
      });
      expect(result.value.requestId).toBe('req-31');
    }
  });

  it('sends the custom header and POST body on the wire', async () => {
    stubApiFetch([
      {
        url: '/api/demo/reqres/inspector?zoom=2',
        method: 'POST',
        body: {
          method: 'POST',
          path: '/api/demo/reqres/inspector',
          queryParams: [],
          headers: [],
          contentType: 'application/json',
          bodyMessage: 'hi',
          requestId: 'req-32',
          requestIdHeader: 'x-request-id',
          reasoning: 'The POST variant.',
        },
      },
    ]);

    const result = await makeRepository().probe({
      method: 'POST',
      query: 'zoom=2',
      headerName: 'X-Probe',
      headerValue: 'hello',
      bodyMessage: 'hi',
    });

    expect(result.ok).toBe(true);
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.headers).toMatchObject({ 'x-probe': 'hello' });
    expect(init?.body).toBe('{"message":"hi"}');
  });

  it('keeps request-conditional fields undefined rather than null (family wire rule)', async () => {
    stubApiFetch([
      {
        url: '/api/demo/reqres/inspector',
        body: {
          method: 'GET',
          path: '/api/demo/reqres/inspector',
          queryParams: [],
          headers: [],
          requestId: 'r',
          requestIdHeader: 'x-request-id',
          reasoning: 'bare.',
        },
      },
    ]);

    const result = await makeRepository().probe({ method: 'GET', query: '' });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.rawQuery).toBeUndefined();
      expect(result.value.contentType).toBeUndefined();
      expect(result.value.client).toBeUndefined();
      expect(result.value.queryParams).toEqual([]);
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().probe({ method: 'GET', query: '' });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards an error envelope into a Failed Result with its diagnostics', async () => {
    stubApiFetch([
      {
        url: '/api/demo/reqres/inspector',
        status: 503,
        body: { error: { code: 'service_unavailable', message: 'calm down', requestId: 'req-4' } },
      },
    ]);

    const result = await makeRepository().probe({ method: 'GET', query: '' });

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
        url: '/api/demo/reqres/inspector?tag=a&tag=b',
        body: { ...reflectedPayload, queryParams: 'not-an-array' },
      },
    ]);

    const result = await makeRepository().probe({ method: 'GET', query: 'tag=a&tag=b' });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
