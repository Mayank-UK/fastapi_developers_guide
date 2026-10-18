import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DepLifecycleApi } from './dep-lifecycle-api';
import { DepLifecycleRepositoryImpl } from './dep-lifecycle-repository-impl';

/**
 * DepLifecycleRepositoryImpl spec — fixture-driven (happy + failure): the
 * span and log payloads round-trip into the domain shape through the
 * guarded GET pipeline; network / envelope / malformed-payload failures
 * (including an unknown span event) all resolve as Failed Results, never
 * throws.
 */

const FIRE_URL = '/api/demo/dep/lifecycle';
const LOG_URL = '/api/demo/dep/lifecycle/log';

const spanPayload = {
  spanId: 'aabbccdd0011',
  setupAt: '2026-10-15T12:00:00.000+00:00',
  handlerOffsetMs: 0,
  pendingEvents: ['teardown'],
};

const logPayload = {
  capacity: 20,
  events: [
    { sequence: 0, spanId: 'aabbccdd0011', event: 'setup', at: 't0', offsetMs: 0 },
    { sequence: 1, spanId: 'aabbccdd0011', event: 'handler', at: 't1', offsetMs: 0 },
    { sequence: 2, spanId: 'aabbccdd0011', event: 'response', at: 't2', offsetMs: 0 },
    { sequence: 3, spanId: 'aabbccdd0011', event: 'teardown', at: 't3', offsetMs: 0 },
  ],
};

function makeRepository(): DepLifecycleRepositoryImpl {
  return new DepLifecycleRepositoryImpl(new DepLifecycleApi(createAppConfig()));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('DepLifecycleRepositoryImpl', () => {
  it('fires a wrapped request and returns the span facts', async () => {
    stubApiFetch([{ url: FIRE_URL, body: spanPayload }]);

    const result = await makeRepository().fire();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.spanId).toBe('aabbccdd0011');
      expect(result.value.pendingEvents).toEqual(['teardown']);
    }
  });

  it('reads the log with every beat sequenced', async () => {
    stubApiFetch([{ url: LOG_URL, body: logPayload }]);

    const result = await makeRepository().log();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.capacity).toBe(20);
      expect(result.value.events.map((event) => event.event)).toEqual([
        'setup',
        'handler',
        'response',
        'teardown',
      ]);
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().log();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards a malformed log (unknown event) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: LOG_URL,
        body: {
          capacity: 20,
          events: [{ sequence: 0, spanId: 'a', event: 'mystery', at: 't', offsetMs: 0 }],
        },
      },
    ]);

    const result = await makeRepository().log();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
