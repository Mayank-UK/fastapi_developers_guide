import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { RuntimeAsyncApi } from './runtime-async-api';
import { RuntimeAsyncRepositoryImpl } from './runtime-async-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * RuntimeAsyncRepositoryImpl spec — fixture-driven (happy + failure): the
 * measured payload round-trips into the domain shape; network / envelope /
 * malformed-payload failures all resolve as Failed Results, never throws.
 */

const demoPayload = {
  ioPlan: [
    { name: 'orders', simulatedIoMs: 60 },
    { name: 'billing', simulatedIoMs: 40 },
    { name: 'inventory', simulatedIoMs: 20 },
  ],
  sequential: {
    strategy: 'sequential',
    elapsedMs: 120.4,
    completionOrder: ['orders', 'billing', 'inventory'],
    perTask: [
      { name: 'orders', simulatedIoMs: 60, measuredMs: 60.1 },
      { name: 'billing', simulatedIoMs: 40, measuredMs: 40.1 },
      { name: 'inventory', simulatedIoMs: 20, measuredMs: 20.1 },
    ],
  },
  gathered: {
    strategy: 'gathered',
    elapsedMs: 60.2,
    completionOrder: ['inventory', 'billing', 'orders'],
    perTask: [
      { name: 'orders', simulatedIoMs: 60, measuredMs: 60.2 },
      { name: 'billing', simulatedIoMs: 40, measuredMs: 40.0 },
      { name: 'inventory', simulatedIoMs: 20, measuredMs: 20.0 },
    ],
  },
  speedup: 2.0,
  trace: [
    { actor: 'alpha', event: 'start' },
    { actor: 'beta', event: 'start' },
    { actor: 'alpha', event: 'step-0' },
    { actor: 'beta', event: 'step-0' },
    { actor: 'alpha', event: 'done' },
    { actor: 'beta', event: 'done' },
  ],
};

function makeRepository(): RuntimeAsyncRepositoryImpl {
  return new RuntimeAsyncRepositoryImpl(new RuntimeAsyncApi(createAppConfig()));
}

describe('RuntimeAsyncRepositoryImpl', () => {
  it('returns a Success carrying the validated domain payload', async () => {
    stubApiFetch([{ url: '/api/demo/runtime/async', body: demoPayload }]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.speedup).toBe(2.0);
      expect(result.value.gathered.completionOrder).toEqual([
        'inventory',
        'billing',
        'orders',
      ]);
      expect(result.value.sequential.perTask[2]?.measuredMs).toBeCloseTo(20.1);
      expect(result.value.trace[0]).toEqual({ actor: 'alpha', event: 'start' });
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
        url: '/api/demo/runtime/async',
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
      // Missing every measured section — the DTO validator must reject it.
      { url: '/api/demo/runtime/async', body: { ioPlan: 'nope' } },
    ]);

    const result = await makeRepository().get();

    expect(result).toEqual(
      failed(
        new ServerFailure('The server response did not match the expected shape.', {
          code: 'invalid_response',
          status: 200,
        }),
      ),
    );
  });

  it('rejects a timing run whose strategy contradicts its position', async () => {
    const swapped = {
      ...demoPayload,
      sequential: demoPayload.gathered,
      gathered: demoPayload.sequential,
    };
    stubApiFetch([{ url: '/api/demo/runtime/async', body: swapped }]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
