import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ArchEventStoreDemo from './eventstore_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetArchEventStoreDemoUseCase } from '../../../domain/demo/get-arch-eventstore-demo-usecase';
import type { ArchEventStorePanel } from '../../../domain/demo/arch-eventstore';

/**
 * ArchEventStoreDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * panel renders the appended history with dense versions, the fold
 * step by step with the rebuild equality, the refused stale write with
 * the unchanged log length, the mutable-row contrast, and the
 * audit_log kinship; a failed read degrades to the shared error panel
 * with recovery.
 */

const fakePanel: ArchEventStorePanel = {
  store: { port: 'EventStore', adapter: 'InMemoryEventStore', stream: 'post:advanced-tour', events: 5 },
  appended: [
    { version: 1, eventType: 'PostCreated', payload: "{'title': 'The advanced architecture tour', 'author': 'ada'}", eventId: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', occurredAt: 't1' },
    { version: 2, eventType: 'PostEdited', payload: "{'title': 'The advanced architecture tour, revised'}", eventId: 'f1e2d3c4b5a697887960514131211100', occurredAt: 't2' },
    { version: 3, eventType: 'TagAdded', payload: "{'tag': 'architecture'}", eventId: '0f1e2d3c4b5a6978879605141312111ff', occurredAt: 't3' },
    { version: 4, eventType: 'TagAdded', payload: "{'tag': 'sagas'}", eventId: '1f1e2d3c4b5a6978879605141312111ee', occurredAt: 't4' },
    { version: 5, eventType: 'PostPublished', payload: '{}', eventId: '2f1e2d3c4b5a6978879605141312111dd', occurredAt: 't5' },
  ],
  foldSteps: [
    { afterVersion: 1, eventType: 'PostCreated', stateNow: "title='The advanced architecture tour' status=draft tags=[none] edits=0" },
    { afterVersion: 2, eventType: 'PostEdited', stateNow: "title='The advanced architecture tour, revised' status=draft tags=[none] edits=1" },
    { afterVersion: 3, eventType: 'TagAdded', stateNow: "title='The advanced architecture tour, revised' status=draft tags=[architecture] edits=1" },
    { afterVersion: 4, eventType: 'TagAdded', stateNow: "title='The advanced architecture tour, revised' status=draft tags=[architecture, sagas] edits=1" },
    { afterVersion: 5, eventType: 'PostPublished', stateNow: "title='The advanced architecture tour, revised' status=published tags=[architecture, sagas] edits=1" },
  ],
  currentState: {
    title: 'The advanced architecture tour, revised',
    author: 'ada',
    tags: ['architecture', 'sagas'],
    edits: 1,
    status: 'published',
  },
  rebuild: {
    method: 'a second InMemoryEventStore instance re-appended the same drafts, then folded',
    state: { title: 'The advanced architecture tour, revised' },
    matches: true,
    evidence: 'fold of stream == fold of replay: True — replay determinism is the property every projection and every rebuild stands on',
  },
  concurrency: {
    writer: 'a rival writer holding a three-versions-stale belief',
    expectedVersion: 3,
    actualVersion: 5,
    storedEventsAfter: 5,
    evidence:
      "VersionConflict: stream 'post:advanced-tour' is at version 5, but the writer expected 3 — the stream moved on; re-read, re-fold, retry — and the log still holds 5 events: the losing write stored nothing",
  },
  contrast: [
    {
      approach: 'mutable row (the familiar way)',
      keeps: 'one row, updated in place — only the latest values',
      history: '4 of the 5 facts gone: the create, the first title, the tag order, when',
      answers: 'what IS the current state? — instantly, but ask it yesterday’s question and the answer is gone',
    },
    {
      approach: 'event stream (this demo’s store)',
      keeps: 'every fact forever, dense versions, nothing rewritten',
      history: '5 of 5 facts retained — the fold replays them in order',
      answers: 'what HAPPENED? — and the state is derived, so new questions (projections) are cheap',
    },
  ],
  kinship: {
    relative: 'audit_log (migration 0001)',
    where: 'server/alembic/versions/0001_guide_schema.py',
    same: 'append-only, identity column, written in the same transaction as the change it records',
    different:
      'a SIDE-BAND record beside mutable rows — event sourcing inverts it: the log is the source of truth and the current state is derived',
  },
  honestyNote:
    'Every row came from real calls on this request: the port’s adapter appended five facts, the fold engine derived the state step by step.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<ArchEventStorePanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetArchEventStoreDemoUseCase, {
    eventstore: () => Promise.resolve(respond()),
  } as unknown as GetArchEventStoreDemoUseCase);
}

describe('ArchEventStoreDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['arch:eventstore']).toBeDefined();
  });

  it('renders the history, the fold with rebuild equality, the refused write, and the kinship', async () => {
    stubUseCase(() => success(fakePanel));

    render(<ArchEventStoreDemo />);

    await waitFor(() => expect(screen.getByTestId('aes-panel')).toBeInTheDocument());

    // The history: dense versions, types, minted ids, clock stamps.
    expect(screen.getByTestId('aes-v-1')).toHaveTextContent('PostCreated');
    expect(screen.getByTestId('aes-v-1')).toHaveTextContent('at t1');
    expect(screen.getByTestId('aes-v-5')).toHaveTextContent('PostPublished');

    // The fold: state after each fact, and the rebuild equality.
    expect(screen.getByTestId('aes-f-1')).toHaveTextContent('status=draft');
    expect(screen.getByTestId('aes-f-4')).toHaveTextContent('tags=[architecture, sagas]');
    expect(screen.getByTestId('aes-f-5')).toHaveTextContent('status=published');
    expect(screen.getByTestId('aes-rebuild')).toHaveTextContent('matches=true');
    expect(screen.getByTestId('aes-rebuild')).toHaveTextContent('replay determinism');

    // The refused stale write: expected 3 vs actual 5, log still 5.
    const conflict = screen.getByTestId('aes-conflict-row');
    expect(conflict).toHaveTextContent('expected v3 vs actual v5');
    expect(conflict).toHaveTextContent('log still 5 events');

    // The contrast + kinship.
    expect(screen.getByTestId('aes-c-mutable')).toHaveTextContent('4 of the 5 facts gone');
    expect(screen.getByTestId('aes-c-event')).toHaveTextContent('5 of 5 facts retained');
    expect(screen.getByTestId('aes-kinship')).toHaveTextContent('audit_log (migration 0001)');
    expect(screen.getByTestId('aes-kinship')).toHaveTextContent('SIDE-BAND');

    expect(screen.getByTestId('aes-honesty-note')).toHaveTextContent('real calls on this request');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The event-store panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-arch-es-1',
            }),
          )
        : success(fakePanel);
    });

    render(<ArchEventStoreDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('aes-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
