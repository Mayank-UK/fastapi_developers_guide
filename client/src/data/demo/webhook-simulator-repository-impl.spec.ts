import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import type { SignedDelivery } from '../../domain/demo/webhook-simulator';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { WebhookSimulatorApi } from './webhook-simulator-api';
import { WebhookSimulatorRepositoryImpl } from './webhook-simulator-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * WebhookSimulatorRepositoryImpl spec — fixture-driven, one endpoint at a
 * time: the roster and a simulation round-trip through their DTOs
 * (optional facts absent-when-null, closed vocabularies enforced), a
 * signed round sends the EXACT body string with its own headers, the
 * tampered round flips exactly one body byte, and both the teaching
 * failure (the 401 envelope) and transport failures resolve as Failed
 * Results, never throws.
 */

const SIMULATOR_URL = '/api/demo/api/webhook-simulator';
const RECEIVE_URL = '/api/demo/api/webhooks/receive';

const rosterPayload = {
  scenarios: [
    {
      id: 'immediate-2xx',
      label: 'Healthy receiver',
      description: 'Answers 200 on the first attempt.',
      successOnAttempt: 1,
    },
    {
      id: 'always-500',
      label: 'Broken receiver',
      description: 'Answers 500 on every attempt.',
      // successOnAttempt omitted — exclude_none on the server side.
    },
  ],
  eventTypes: ['post.published', 'post.updated', 'comment.created'],
  secret: 'whsec_fixture',
  receiveEndpoint: RECEIVE_URL,
  policy: { maxAttempts: 5, baseDelaySeconds: 1, backoffFactor: 2, offsets: [0, 1, 3, 7, 15] },
  reasoning: 'The policy allows 5 attempts at offsets [0, 1, 3, 7, 15] seconds.',
};

const handRound: SignedDelivery = {
  method: 'POST',
  url: RECEIVE_URL,
  headers: {
    'content-type': 'application/json',
    'x-webhook-timestamp': '1760000000',
    'x-webhook-signature': 'v1=fixture',
  },
  body: '{"id":"evt_fixture"}',
};

const simulationPayload = {
  subscription: {
    id: 'sub_fixture',
    url: 'https://client.example/hooks/sub_fixture',
    scenario: 'flaky-then-success',
  },
  event: {
    id: 'evt_fixture',
    type: 'post.published',
    body: { createdAt: '2026-10-15T10:00:00+00:00', data: { note: 'x' }, id: 'evt_fixture', type: 'post.published' },
  },
  secret: 'whsec_fixture',
  policy: rosterPayload.policy,
  attempts: [
    { attempt: 1, offsetSeconds: 0, timestamp: 1_760_000_000, signature: 'v1=aa', status: 500, outcome: 'retry-scheduled' },
    { attempt: 2, offsetSeconds: 1, timestamp: 1_760_000_001, signature: 'v1=bb', status: 500, outcome: 'retry-scheduled' },
    { attempt: 3, offsetSeconds: 3, timestamp: 1_760_000_003, signature: 'v1=cc', status: 200, outcome: 'delivered' },
  ],
  verdict: 'delivered',
  deliveredAtOffset: 3,
  deliverByHand: handRound,
  reasoning: 'Subscription sub_fixture fired post.published: 3 attempt(s).',
};

const receiptPayload = {
  eventId: 'evt_fixture',
  receivedAt: 1_760_000_010,
  ageSeconds: 10,
  detail: 'Signature verified in constant time over the raw request bytes.',
};

function makeRepository(): WebhookSimulatorRepositoryImpl {
  return new WebhookSimulatorRepositoryImpl(new WebhookSimulatorApi(createAppConfig()));
}

describe('WebhookSimulatorRepositoryImpl', () => {
  it('fetches and parses the roster (absent successOnAttempt stays undefined)', async () => {
    stubApiFetch([{ url: SIMULATOR_URL, method: 'GET', body: rosterPayload }]);

    const result = await makeRepository().roster();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.scenarios.map((card) => card.id)).toEqual(['immediate-2xx', 'always-500']);
      expect(result.value.scenarios[0]?.successOnAttempt).toBe(1);
      expect(result.value.scenarios[1]?.successOnAttempt).toBeUndefined();
      expect(result.value.policy.offsets).toEqual([0, 1, 3, 7, 15]);
      expect(result.value.receiveEndpoint).toBe(RECEIVE_URL);
    }
  });

  it('parses a simulation with optional facts present', async () => {
    stubApiFetch([{ url: SIMULATOR_URL, method: 'POST', body: simulationPayload }]);

    const result = await makeRepository().simulate({
      eventType: 'post.published',
      scenario: 'flaky-then-success',
      note: 'x',
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.verdict).toBe('delivered');
      expect(result.value.deliveredAtOffset).toBe(3);
      expect(result.value.deadLetter).toBeUndefined();
      expect(result.value.attempts).toHaveLength(3);
      expect(result.value.attempts[2]?.outcome).toBe('delivered');
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe(
      '{"eventType":"post.published","scenario":"flaky-then-success","note":"x"}',
    );
  });

  it('parses a dead-lettered simulation with the DLQ entry and no deliveredAtOffset', async () => {
    stubApiFetch([
      {
        url: SIMULATOR_URL,
        method: 'POST',
        body: {
          ...simulationPayload,
          attempts: simulationPayload.attempts.slice(0, 1),
          verdict: 'dead-lettered',
          deliveredAtOffset: undefined,
          deadLetter: {
            eventId: 'evt_fixture',
            attempts: 5,
            lastStatus: 500,
            finalOffsetSeconds: 15,
            reason: 'parked for inspection and replay.',
          },
        },
      },
    ]);

    const result = await makeRepository().simulate({
      eventType: 'post.published',
      scenario: 'always-500',
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.verdict).toBe('dead-lettered');
      expect(result.value.deliveredAtOffset).toBeUndefined();
      expect(result.value.deadLetter?.attempts).toBe(5);
      expect(result.value.deadLetter?.finalOffsetSeconds).toBe(15);
    }
  });

  it('rejects an unknown scenario spelling loudly (invalid_response)', async () => {
    stubApiFetch([
      {
        url: SIMULATOR_URL,
        method: 'POST',
        body: { ...simulationPayload, verdict: 'sometimes-418' },
      },
    ]);

    const result = await makeRepository().simulate({
      eventType: 'post.published',
      scenario: 'immediate-2xx',
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('delivers the signed round with the EXACT body string and its own headers', async () => {
    stubApiFetch([{ url: RECEIVE_URL, method: 'POST', body: receiptPayload, status: 202 }]);

    const result = await makeRepository().deliver(simulationPayload.deliverByHand);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.eventId).toBe('evt_fixture');
      expect(result.value.ageSeconds).toBe(10);
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.body).toBe(simulationPayload.deliverByHand.body);
    expect(init?.headers).toEqual(
      expect.objectContaining({
        'content-type': 'application/json',
        'x-webhook-timestamp': '1760000000',
        'x-webhook-signature': 'v1=fixture',
      }),
    );
  });

  it('tampered delivery flips exactly one body byte and guards the 401 envelope', async () => {
    stubApiFetch([
      {
        url: RECEIVE_URL,
        method: 'POST',
        status: 401,
        body: {
          error: {
            code: 'unauthorized',
            message: 'Webhook signature mismatch: the payload does not match the shared secret.',
            requestId: 'req-w14',
          },
        },
      },
    ]);

    const result = await makeRepository().deliverTampered(simulationPayload.deliverByHand);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('unauthorized');
      expect(result.failure.status).toBe(401);
      expect(result.failure.message).toContain('signature mismatch');
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    const sentBody = typeof init?.body === 'string' ? init.body : '';
    expect(sentBody).toBe('{"id":"evt_fixture"' + '{');
    expect(simulationPayload.deliverByHand.body.endsWith('}')).toBe(true);
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().roster();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards a malformed payload into a Failed Result', async () => {
    stubApiFetch([{ url: SIMULATOR_URL, method: 'GET', body: { hello: 'world' } }]);

    const result = await makeRepository().roster();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
