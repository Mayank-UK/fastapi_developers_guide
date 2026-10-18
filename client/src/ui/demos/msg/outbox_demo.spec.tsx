import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { OutboxDemo } from './outbox_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetMsgOutboxDemoUseCase } from '../../../domain/demo/get-msg-outbox-demo-usecase';
import type {
  OutboxConsumeOutcome,
  OutboxRow,
  OutboxPanel,
  OutboxWriteOutcome,
  RelayOutcome,
} from '../../../domain/demo/msg-outbox';

/**
 * OutboxDemo spec — fixture-driven (happy + failure): the roster renders
 * the table counts and telemetry; the create button shows BOTH halves of
 * the one-transaction write; the relay buttons show the normal and the
 * crashed cycle; the consume button shows the exactly-once-effect counts;
 * failures degrade to the shared error panel with recovery.
 */

const panel: OutboxPanel = {
  namespace: 'guide_demo:msg:*',
  stream: 'guide_demo:msg:outbox-events',
  table: 'outbox',
  stats: { total: 1, published: 0, unpublished: 1 },
  outbox: [
    {
      eventId: '0192b0c0-0000-7000-8000-000000000001',
      eventType: 'post.created',
      aggregate: 'posts:42',
      payload: '{"postId": 42}',
      createdAt: '2026-10-16T00:00:00+00:00',
      publishedAt: null,
    },
  ],
  streamEntries: [],
  telemetry: {
    creates: 1,
    relayCycles: 0,
    crashSimulations: 0,
    publishes: 0,
    eventsProcessed: 0,
    duplicatesSkipped: 0,
  },
  postsEndpoint: '/api/demo/msg/outbox/posts',
  relayEndpoint: '/api/demo/msg/outbox/relay',
  consumeEndpoint: '/api/demo/msg/outbox/consume',
  reasoning: 'One PostgreSQL table and one Redis Stream, bridged by a relay.',
};

const outboxRow = panel.outbox[0] as OutboxRow;

const writeOutcome: OutboxWriteOutcome = {
  committed: true,
  post: {
    id: 42,
    slug: 'a-post-born-with-its-event-0192b0c0',
    title: 'A post born with its event',
    author: 'Alan Kay',
    createdAt: '2026-10-16T00:00:00+00:00',
  },
  event: outboxRow,
  failure: null,
  detail: 'post 42 and its event committed in ONE transaction',
};

const relayOutcome: RelayOutcome = {
  cycle: 1,
  stream: panel.stream,
  discovered: 1,
  published: [
    {
      eventId: outboxRow.eventId,
      entryId: '1792160000000-0',
      aggregate: 'posts:42',
    },
  ],
  marked: 1,
  crashed: false,
  detail: 'published each and stamped published_at on 1',
};

const crashedOutcome: RelayOutcome = {
  ...relayOutcome,
  marked: 0,
  crashed: true,
  detail: 'published then DIED before marking — the rows stay unpublished',
};

const consumeOutcome: OutboxConsumeOutcome = {
  stream: panel.stream,
  entries: 2,
  processed: 1,
  skippedDuplicates: 1,
  proof: '2 stream entries → 1 processed, 1 duplicate skipped — the exactly-once EFFECT',
};

type Stubs = {
  panel?: () => Promise<Result<OutboxPanel>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetMsgOutboxDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    create: async () => success(writeOutcome),
    relay: async (crashBeforeMark: boolean) =>
      success(crashBeforeMark ? crashedOutcome : relayOutcome),
    consume: async () => success(consumeOutcome),
  } as unknown as GetMsgOutboxDemoUseCase);
}

describe('OutboxDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['msg:outbox']).toBeDefined();
  });

  it('renders the roster with the table counts and telemetry', async () => {
    stubUseCase({});
    render(<OutboxDemo />);
    await waitFor(() => expect(screen.getByTestId('msg-outbox-state')).toBeInTheDocument());
    expect(screen.getByTestId('msg-outbox-stats')).toHaveTextContent(
      'total 1 · published 0 · unpublished 1',
    );
    expect(screen.getByTestId('msg-outbox-state')).toHaveTextContent('posts:42 · unpublished');
    expect(screen.getByTestId('msg-outbox-reasoning')).toHaveTextContent('bridged by a relay');
  });

  it('shows both halves of the write, the crash window, and the dedupe proof', async () => {
    stubUseCase({});
    render(<OutboxDemo />);
    await waitFor(() => expect(screen.getByTestId('msg-outbox-state')).toBeInTheDocument());

    screen.getByRole('button', { name: 'create post + event (one tx)' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-outbox-write')).toBeInTheDocument());
    expect(screen.getByTestId('msg-outbox-write')).toHaveTextContent('committed — both halves');
    expect(screen.getByTestId('msg-outbox-write')).toHaveTextContent('post 42 ·');
    expect(screen.getByTestId('msg-outbox-write')).toHaveTextContent('event 0192b0c0');

    screen.getByRole('button', { name: 'relay + crash window' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-outbox-relay')).toBeInTheDocument());
    expect(screen.getByTestId('msg-outbox-relay')).toHaveTextContent(
      'marked 0 · CRASHED before marking',
    );

    screen.getByRole('button', { name: 'consume (dedupe)' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-outbox-consume')).toBeInTheDocument());
    expect(screen.getByTestId('msg-outbox-consume')).toHaveTextContent(
      '2 entries → processed 1 · skipped 1',
    );
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('PostgreSQL is unreachable.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-m2',
              }),
            )
          : success(panel);
      },
    });

    render(<OutboxDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('msg-outbox-state')).toBeInTheDocument());
  });
});
