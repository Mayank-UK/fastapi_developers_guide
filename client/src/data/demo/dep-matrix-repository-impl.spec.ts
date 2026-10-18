import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DepMatrixApi } from './dep-matrix-api';
import { DepMatrixRepositoryImpl } from './dep-matrix-repository-impl';

/**
 * DepMatrixRepositoryImpl spec — fixture-driven (happy + failure): the
 * matrix payload round-trips into the domain shape through the guarded
 * GET pipeline; network / envelope / malformed-payload failures
 * (including an unknown verdict) all resolve as Failed Results, never
 * throws.
 */

const MATRIX_URL = '/api/demo/dep/matrix';

const matrixPayload = {
  rows: [
    {
      flavor: 'cached-x2',
      label: 'same dependency asked twice (use_cache=True default)',
      tokens: ['RateBudget#f1', 'RateBudget#f1'],
      verdict: 'same-instance',
    },
    {
      flavor: 'sync-in-async',
      label: 'sync provider inside an async endpoint: threadpool vs event loop',
      tokens: ['dep-thread:AnyIO worker thread', 'handler-thread:asyncio-portal-x'],
      verdict: 'threadpool',
    },
  ],
};

function makeRepository(): DepMatrixRepositoryImpl {
  return new DepMatrixRepositoryImpl(new DepMatrixApi(createAppConfig()));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('DepMatrixRepositoryImpl', () => {
  it('resolves the matrix and returns every row with its verdict', async () => {
    stubApiFetch([{ url: MATRIX_URL, body: matrixPayload }]);

    const result = await makeRepository().matrix();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.rows).toHaveLength(2);
      expect(result.value.rows[0]?.verdict).toBe('same-instance');
      expect(result.value.rows[1]?.tokens[0]).toBe('dep-thread:AnyIO worker thread');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().matrix();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards an error envelope into a Failed Result', async () => {
    stubApiFetch([
      {
        url: MATRIX_URL,
        status: 500,
        body: {
          error: {
            code: 'internal',
            message: 'Unexpected server error.',
            requestId: 'req-70',
          },
        },
      },
    ]);

    const result = await makeRepository().matrix();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('internal');
      expect(result.failure.status).toBe(500);
    }
  });

  it('guards a malformed matrix (unknown verdict) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: MATRIX_URL,
        body: {
          rows: [{ flavor: 'x', label: 'y', tokens: ['z'], verdict: 'mystery' }],
        },
      },
    ]);

    const result = await makeRepository().matrix();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
