import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { StreamDemo } from './stream_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetMsgStreamDemoUseCase } from '../../../domain/demo/get-msg-stream-demo-usecase';
import type {
  ConsumeOutcome,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamPanel,
} from '../../../domain/demo/msg-stream';

/**
 * StreamDemo spec — fixture-driven (happy + failure): the roster renders
 * the stream's facts (length, last id, pending count, trailing entries);
 * the produce / healthy / poison / pending / reclaim buttons render their
 * outcomes and the pending rows with owner and delivery counts; failures
 * degrade to the shared error panel with recovery.
 */

const panel: StreamPanel = {
  namespace: 'guide_demo:msg:*',
  stream: 'guide_demo:msg:stream',
  group: 'guide_demo:msg:workers',
  healthyConsumer: 'healthy-worker',
  poisonConsumer: 'poison-worker',
  length: 2,
  displayed: 2,
  lastId: '1792157746389-0',
  entries: [
    {
      id: '1792157746349-0',
      eventId: '0192b0c0-0000-7000-8000-000000000001',
      eventType: 'demo.note',
      payload: '{"note": "one"}',
    },
    {
      id: '1792157746389-0',
      eventId: '0192b0c0-0000-7000-8000-000000000002',
      eventType: 'demo.note',
      payload: '{"note": "two"}',
    },
  ],
  pendingCount: 1,
  produceEndpoint: '/api/demo/msg/stream/produce',
  consumeEndpoint: '/api/demo/msg/stream/consume',
  pendingEndpoint: '/api/demo/msg/stream/pending',
  reclaimEndpoint: '/api/demo/msg/stream/reclaim',
  reasoning: 'One Redis Stream, one consumer group, two consumer personas.',
};

const produceOutcome: ProduceOutcome = {
  stream: panel.stream,
  eventId: '0192b0c0-0000-7000-8000-000000000003',
  entryId: '1792160000000-0',
  note: 'hello from the panel',
  length: 3,
  detail: 'XADD appended the entry — the id order is the arrival order',
};

const healthyOutcome: ConsumeOutcome = {
  stream: panel.stream,
  group: panel.group,
  consumer: 'healthy-worker',
  mode: 'healthy',
  delivered: panel.entries,
  acked: 2,
  detail: 'read 2 new entries and acknowledged 2',
};

const poisonOutcome: ConsumeOutcome = {
  ...healthyOutcome,
  consumer: 'poison-worker',
  mode: 'poison',
  acked: 0,
  detail: 'read 2 new entries and NEVER ACKED — they sit pending',
};

const pendingOutcome: PendingListOutcome = {
  stream: panel.stream,
  group: panel.group,
  entries: [
    {
      entryId: '1792157746349-0',
      consumer: 'poison-worker',
      idleMs: 1200,
      deliveries: 1,
    },
  ],
  detail: '1 pending entry, owned by poison-worker',
};

const reclaimOutcome: ReclaimOutcome = {
  stream: panel.stream,
  group: panel.group,
  consumer: 'healthy-worker',
  minIdleMs: 0,
  claimed: panel.entries.slice(0, 1),
  acked: 1,
  detail: 'XAUTOCLAIM moved 1 entry and finished the work',
};

type Stubs = {
  panel?: () => Promise<Result<StreamPanel>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetMsgStreamDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    produce: async () => success(produceOutcome),
    consume: async (mode: 'healthy' | 'poison') =>
      success(mode === 'healthy' ? healthyOutcome : poisonOutcome),
    pending: async () => success(pendingOutcome),
    reclaim: async () => success(reclaimOutcome),
  } as unknown as GetMsgStreamDemoUseCase);
}

describe('StreamDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['msg:stream']).toBeDefined();
  });

  it('renders the roster with the log facts and personas', async () => {
    stubUseCase({});
    render(<StreamDemo />);
    await waitFor(() => expect(screen.getByTestId('msg-stream-state')).toBeInTheDocument());
    expect(screen.getByTestId('msg-stream-facts')).toHaveTextContent(
      'length 2 · last 1792157746389-0 · pending 1',
    );
    expect(screen.getByTestId('msg-stream-state')).toHaveTextContent('{"note": "two"}');
    expect(screen.getByTestId('msg-stream-reasoning')).toHaveTextContent('two consumer personas');
  });

  it('renders the produce, poison, pending, and reclaim outcomes', async () => {
    stubUseCase({});
    render(<StreamDemo />);
    await waitFor(() => expect(screen.getByTestId('msg-stream-state')).toBeInTheDocument());

    screen.getByRole('button', { name: 'produce (XADD)' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-stream-outcome')).toBeInTheDocument());
    expect(screen.getByTestId('msg-stream-outcome')).toHaveTextContent(
      'produce → 1792160000000-0',
    );

    screen.getByRole('button', { name: 'consume poison → no ack' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('msg-stream-outcome')).toHaveTextContent(
        'poison read → delivered 2, acked 0',
      ),
    );

    screen.getByRole('button', { name: 'pending list' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-stream-pending')).toBeInTheDocument());
    expect(screen.getByTestId('msg-stream-pending')).toHaveTextContent(
      'poison-worker · idle 1200ms · deliveries 1',
    );

    screen.getByRole('button', { name: 'reclaim (XAUTOCLAIM)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('msg-stream-outcome')).toHaveTextContent(
        'reclaim → claimed 1, acked 1',
      ),
    );
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Redis is unreachable.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-m1',
              }),
            )
          : success(panel);
      },
    });

    render(<StreamDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-stream-state')).toBeInTheDocument());
  });
});
