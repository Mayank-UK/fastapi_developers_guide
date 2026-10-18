import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { WebhookSimulatorDemo } from './webhook_simulator_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetWebhookSimulatorDemoUseCase } from '../../../domain/demo/get-webhook-simulator-demo-usecase';
import type {
  SignedDelivery,
  WebhookReceipt,
  WebhookSimulation,
  WebhookSimulatorRequest,
  WebhookSimulatorRoster,
} from '../../../domain/demo/webhook-simulator';

/**
 * WebhookSimulatorDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration instead of stubbing fetch. Behavior, not
 * implementation: the roster renders the secret and the schedule,
 * firing walks the chosen scenario's lifecycle (attempts, verdict, the
 * dead letter when the budget spent), the deliver-by-hand section fires
 * the REAL signed round (202 receipt inline) and the tampered round
 * (the 401 envelope rendered inline as the lesson, never the error
 * panel), and roster failures degrade to the shared error panel with
 * recovery.
 */

const roster: WebhookSimulatorRoster = {
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
    },
    {
      id: 'flaky-then-success',
      label: 'Flaky receiver',
      description: 'Answers 200 on the third attempt.',
      successOnAttempt: 3,
    },
  ],
  eventTypes: ['post.published', 'post.updated', 'comment.created'],
  secret: 'whsec_spec_secret',
  receiveEndpoint: '/api/demo/api/webhooks/receive',
  policy: { maxAttempts: 5, baseDelaySeconds: 1, backoffFactor: 2, offsets: [0, 1, 3, 7, 15] },
  reasoning: 'The schedule is exact because the engine is deliberately jitter-free.',
};

const signedRound: SignedDelivery = {
  method: 'POST',
  url: '/api/demo/api/webhooks/receive',
  headers: {
    'content-type': 'application/json',
    'x-webhook-timestamp': '1760000000',
    'x-webhook-signature': 'v1=spec',
  },
  body: '{"id":"evt_spec"}',
};

const flakySimulation: WebhookSimulation = {
  subscription: {
    id: 'sub_spec',
    url: 'https://client.example/hooks/sub_spec',
    scenario: 'flaky-then-success',
  },
  event: { id: 'evt_spec', type: 'post.published', body: { id: 'evt_spec', data: { note: 'x' } } },
  secret: 'whsec_spec_secret',
  policy: roster.policy,
  attempts: [
    { attempt: 1, offsetSeconds: 0, timestamp: 1_760_000_000, signature: 'v1=aa', status: 500, outcome: 'retry-scheduled' },
    { attempt: 2, offsetSeconds: 1, timestamp: 1_760_000_001, signature: 'v1=bb', status: 500, outcome: 'retry-scheduled' },
    { attempt: 3, offsetSeconds: 3, timestamp: 1_760_000_003, signature: 'v1=cc', status: 200, outcome: 'delivered' },
  ],
  verdict: 'delivered',
  deliveredAtOffset: 3,
  deliverByHand: signedRound,
  reasoning: '3 attempt(s) at offsets 0,1,3s. Delivered on attempt 3.',
};

const deadLetteredSimulation: WebhookSimulation = {
  ...flakySimulation,
  attempts: [
    { attempt: 1, offsetSeconds: 0, timestamp: 1_760_000_000, signature: 'v1=aa', status: 500, outcome: 'retry-scheduled' },
  ],
  verdict: 'dead-lettered',
  deliveredAtOffset: undefined,
  deadLetter: {
    eventId: 'evt_spec',
    attempts: 5,
    lastStatus: 500,
    finalOffsetSeconds: 15,
    reason: 'parked for inspection and replay.',
  },
};

const receipt: WebhookReceipt = {
  eventId: 'evt_spec',
  receivedAt: 1_760_000_010,
  ageSeconds: 10,
  detail: 'Signature verified in constant time over the raw request bytes.',
};

const refusedFailure = new ServerFailure(
  'Webhook signature mismatch: the payload does not match the shared secret.',
  { code: 'unauthorized', status: 401, requestId: 'req-ws' },
);

type StubUseCase = {
  roster: () => Promise<Result<WebhookSimulatorRoster>>;
  simulate: (request: WebhookSimulatorRequest) => Promise<Result<WebhookSimulation>>;
  deliver: (signed: SignedDelivery) => Promise<Result<WebhookReceipt>>;
  deliverTampered: (signed: SignedDelivery) => Promise<Result<WebhookReceipt>>;
};

function stubUseCase(overrides: Partial<StubUseCase>): void {
  container.initialize(createAppConfig());
  const useCase = {
    roster: async () => success(roster),
    simulate: async () => success(flakySimulation),
    deliver: async () => success(receipt),
    deliverTampered: async () => failed(refusedFailure),
    ...overrides,
  };
  container.register(
    ContainerTokens.GetWebhookSimulatorDemoUseCase,
    useCase as unknown as GetWebhookSimulatorDemoUseCase,
  );
}

describe('WebhookSimulatorDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['api:webhook-simulator']).toBeDefined();
  });

  it('renders loading first, then the roster: secret, schedule, scenario chips', async () => {
    stubUseCase({});

    render(<WebhookSimulatorDemo />);

    expect(screen.getByTestId('ws-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('ws-roster')).toBeInTheDocument());
    expect(screen.getByTestId('ws-facts')).toHaveTextContent('whsec_spec_secret');
    expect(screen.getByTestId('ws-facts')).toHaveTextContent('+0s +1s +3s +7s +15s');
    expect(screen.getAllByTestId('ws-scenario')).toHaveLength(3);
    expect(screen.getByTestId('ws-reasoning')).toHaveTextContent('jitter-free');
  });

  it('fires the chosen scenario and renders its attempts, verdict, and reasoning', async () => {
    const fired: WebhookSimulatorRequest[] = [];
    stubUseCase({
      simulate: async (request) => (fired.push(request), success(flakySimulation)),
    });

    render(<WebhookSimulatorDemo />);
    await waitFor(() => expect(screen.getByTestId('ws-roster')).toBeInTheDocument());

    fireEvent.change(screen.getByTestId('ws-event-type'), { target: { value: 'post.updated' } });
    fireEvent.change(screen.getByTestId('ws-note'), { target: { value: 'a spec note' } });
    fireEvent.click(screen.getByTestId('ws-fire'));

    await waitFor(() => expect(screen.getByTestId('ws-result')).toBeInTheDocument());
    expect(fired).toEqual([
      { eventType: 'post.updated', scenario: 'flaky-then-success', note: 'a spec note' },
    ]);
    expect(screen.getAllByTestId('ws-attempt')).toHaveLength(3);
    expect(screen.getByTestId('ws-verdict')).toHaveTextContent('delivered on attempt 3 at +3s');
    expect(screen.queryByTestId('ws-dead-letter')).not.toBeInTheDocument();
    expect(screen.getByTestId('ws-simulation-reasoning')).toHaveTextContent('Delivered on attempt 3');
  });

  it('renders the dead-letter entry when the budget is spent', async () => {
    stubUseCase({ simulate: async () => success(deadLetteredSimulation) });

    render(<WebhookSimulatorDemo />);
    await waitFor(() => expect(screen.getByTestId('ws-roster')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('ws-fire'));

    await waitFor(() => expect(screen.getByTestId('ws-result')).toBeInTheDocument());
    expect(screen.getByTestId('ws-verdict')).toHaveTextContent('dead-lettered after 1 attempt(s)');
    expect(screen.getByTestId('ws-dead-letter')).toHaveTextContent('parked for inspection and replay');
    expect(screen.getByTestId('ws-dead-letter')).toHaveTextContent('+15s');
  });

  it('delivers the signed round for real and renders the 202 receipt inline', async () => {
    const delivered: SignedDelivery[] = [];
    stubUseCase({ deliver: async (signed) => (delivered.push(signed), success(receipt)) });

    render(<WebhookSimulatorDemo />);
    await waitFor(() => expect(screen.getByTestId('ws-roster')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('ws-fire'));
    await waitFor(() => expect(screen.getByTestId('ws-result')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('ws-deliver-signed'));

    await waitFor(() => expect(screen.getByTestId('ws-deliver-accepted')).toBeInTheDocument());
    expect(delivered).toEqual([signedRound]);
    expect(screen.getByTestId('ws-deliver-accepted')).toHaveTextContent('202 Accepted');
    expect(screen.getByTestId('ws-deliver-accepted')).toHaveTextContent('evt_spec');
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('renders the tampered round as the inline 401 refusal, not an error panel', async () => {
    const tampered: SignedDelivery[] = [];
    stubUseCase({
      deliverTampered: async (signed) => (tampered.push(signed), failed(refusedFailure)),
    });

    render(<WebhookSimulatorDemo />);
    await waitFor(() => expect(screen.getByTestId('ws-roster')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('ws-fire'));
    await waitFor(() => expect(screen.getByTestId('ws-result')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('ws-deliver-tampered'));

    await waitFor(() => expect(screen.getByTestId('ws-deliver-refused')).toBeInTheDocument());
    expect(tampered).toEqual([signedRound]);
    expect(screen.getByTestId('ws-deliver-refused')).toHaveTextContent('401 unauthorized');
    expect(screen.getByTestId('ws-deliver-refused')).toHaveTextContent('signature mismatch');
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('degrades to the shared error panel on a Failed roster, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      roster: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('The simulator is down.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-w14',
              }),
            )
          : success(roster);
      },
    });

    render(<WebhookSimulatorDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(screen.getByTestId('ws-roster')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
