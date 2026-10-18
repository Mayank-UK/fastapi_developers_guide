import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { MiddlewarePipelineApi } from './middleware-pipeline-api';
import { MiddlewarePipelineRepositoryImpl } from './middleware-pipeline-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * MiddlewarePipelineRepositoryImpl spec — fixture-driven (happy + failure):
 * the pipeline payload round-trips into the domain shape (stack rows with
 * kinds, the traced onion, both side orders, the request id); network /
 * envelope / malformed-payload failures all resolve as Failed Results,
 * never throws.
 */

const DEMO_URL = '/api/demo/middleware/pipeline';

const payload = {
  stack: [
    {
      name: 'ServerErrorMiddleware',
      kind: 'framework',
      orderIndex: 0,
      role: "Starlette's outermost bookend — the last-resort 500 handler.",
    },
    {
      name: 'RequestIdMiddleware',
      kind: 'user',
      orderIndex: 2,
      role: "this app's request-id layer.",
    },
    {
      name: 'APIRouter',
      kind: 'router',
      orderIndex: 5,
      role: 'the terminal ASGI app.',
    },
  ],
  trace: [
    { stage: 'ServerErrorMiddleware', phase: 'request', sequence: 0, note: 'descends' },
    { stage: 'RequestIdMiddleware', phase: 'request', sequence: 1, note: 'descends' },
    { stage: 'APIRouter', phase: 'handler', sequence: 2, note: 'endpoint runs once' },
    { stage: 'RequestIdMiddleware', phase: 'response', sequence: 3, note: 'ascends' },
    { stage: 'ServerErrorMiddleware', phase: 'response', sequence: 4, note: 'ascends' },
  ],
  requestSideOrder: ['ServerErrorMiddleware', 'RequestIdMiddleware', 'APIRouter'],
  responseSideOrder: ['APIRouter', 'RequestIdMiddleware', 'ServerErrorMiddleware'],
  requestId: 'trace-probe-9',
  requestIdHeader: 'x-request-id',
  reasoning: 'The request descends; the response unwinds in reverse.',
};

function makeRepository(): MiddlewarePipelineRepositoryImpl {
  return new MiddlewarePipelineRepositoryImpl(new MiddlewarePipelineApi(createAppConfig()));
}

describe('MiddlewarePipelineRepositoryImpl', () => {
  it('returns a Success with the validated pipeline payload', async () => {
    stubApiFetch([{ url: DEMO_URL, body: payload }]);

    const result = await makeRepository().read();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.stack[1]).toEqual({
        name: 'RequestIdMiddleware',
        kind: 'user',
        orderIndex: 2,
        role: "this app's request-id layer.",
      });
      expect(result.value.trace[2]?.phase).toBe('handler');
      expect(result.value.responseSideOrder[0]).toBe('APIRouter');
      expect(result.value.requestId).toBe('trace-probe-9');
    }
  });

  it('rejects an unknown stack kind as an invalid payload (closed sets)', async () => {
    const badKind = { name: 'AMiddleware', kind: 'mystery', orderIndex: 0, role: 'unknown' };
    stubApiFetch([{ url: DEMO_URL, body: { ...payload, stack: [badKind] } }]);

    const result = await makeRepository().read();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('rejects an unknown trace phase as an invalid payload', async () => {
    const badPhase = { stage: 'AMiddleware', phase: 'teatime', sequence: 0, note: '?' };
    stubApiFetch([{ url: DEMO_URL, body: { ...payload, trace: [badPhase] } }]);

    const result = await makeRepository().read();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().read();

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
        body: { error: { code: 'service_unavailable', message: 'calm down', requestId: 'req-8' } },
      },
    ]);

    const result = await makeRepository().read();

    expect(result).toEqual(
      failed(
        new ServerFailure('calm down', {
          code: 'service_unavailable',
          status: 503,
          requestId: 'req-8',
        }),
      ),
    );
  });
});
