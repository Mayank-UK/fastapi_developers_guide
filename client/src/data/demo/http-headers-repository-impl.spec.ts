import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { HttpHeadersApi } from './http-headers-api';
import { HttpHeadersRepositoryImpl } from './http-headers-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * HttpHeadersRepositoryImpl spec — fixture-driven (happy + failure): the
 * echo payload round-trips into the domain shape (and the request is sent
 * with the chosen method, custom header, and POST body); network /
 * envelope / malformed-payload failures all resolve as Failed Results,
 * never throws.
 */

const DEMO_URL = '/api/demo/http/headers?from=client-demo';

const echoPayload = {
  method: 'POST',
  path: '/api/demo/http/headers',
  query: 'from=client-demo',
  contentType: 'application/json',
  bodyMessage: 'hello',
  headers: [
    {
      name: 'content-type',
      value: 'application/json',
      scope: 'end-to-end',
      note: 'the request body’s media type — the contract the server parses by',
    },
    { name: 'x-demo-trace', value: 'hello-http', scope: 'end-to-end' },
  ],
  hopByHop: [
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
  ],
};

function makeRepository(): HttpHeadersRepositoryImpl {
  return new HttpHeadersRepositoryImpl(new HttpHeadersApi(createAppConfig()));
}

describe('HttpHeadersRepositoryImpl', () => {
  it('sends the configured request and returns a Success with the validated echo', async () => {
    let seenInit: RequestInit | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        seenInit = init;
        return {
          ok: true,
          status: 200,
          json: async () => echoPayload,
        };
      }),
    );

    const result = await makeRepository().send({
      method: 'POST',
      headerName: 'x-demo-trace',
      headerValue: 'hello-http',
      message: 'hello',
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.method).toBe('POST');
      expect(result.value.contentType).toBe('application/json');
      expect(result.value.bodyMessage).toBe('hello');
      expect(result.value.headers[1]).toEqual({
        name: 'x-demo-trace',
        value: 'hello-http',
        scope: 'end-to-end',
      });
    }
    expect(seenInit?.method).toBe('POST');
    expect(seenInit?.headers).toEqual({
      accept: 'application/json',
      'x-demo-trace': 'hello-http',
    });
    expect(seenInit?.body).toBe(JSON.stringify({ message: 'hello' }));
  });

  it('sends a GET without a body or custom headers when none are configured', async () => {
    let seenInit: RequestInit | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        seenInit = init;
        return {
          ok: true,
          status: 200,
          json: async () => ({ ...echoPayload, method: 'GET', contentType: undefined, bodyMessage: undefined }),
        };
      }),
    );

    const result = await makeRepository().send({ method: 'GET' });

    expect(result.ok).toBe(true);
    expect(seenInit?.method).toBe('GET');
    expect(seenInit?.body).toBeUndefined();
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().send({ method: 'GET' });

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

    const result = await makeRepository().send({ method: 'POST', message: 'x' });

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
      // An unknown scope must be rejected by the DTO validator.
      {
        url: DEMO_URL,
        body: { method: 'GET', path: '/x', headers: [{ name: 'a', value: 'b', scope: 'mystery' }] },
      },
    ]);

    const result = await makeRepository().send({ method: 'GET' });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
