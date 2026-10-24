import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ArchSagaDemo from './saga_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetArchSagaDemoUseCase } from '../../../domain/demo/get-arch-saga-demo-usecase';
import type { ArchSagaPanel } from '../../../domain/demo/arch-saga';

/**
 * ArchSagaDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the
 * token registration (the documented replace-a-singleton seam) instead
 * of stubbing fetch. Behavior, not implementation: the panel renders
 * the workflow's four steps with their compensations, the committed
 * run's forward log, the failing run's REVERSED compensation order
 * with per-step evidence, the balance rows proving the undo, and the
 * durability links; a failed read degrades to the shared error panel
 * with recovery.
 */

const fakePanel: ArchSagaPanel = {
  workflow: {
    name: 'order-fulfillment',
    steps: [
      {
        action: 'reserve-item',
        compensates: 'release-item',
        describes: 'hold one unit of stock locally (a real transaction)',
      },
      { action: 'charge-card', compensates: 'refund-card', describes: 'take payment at the payment service' },
      { action: 'book-shipment', compensates: 'cancel-shipment', describes: 'reserve a delivery slot at the carrier' },
      { action: 'announce-order', compensates: 'retract-announce', describes: 'publish the order-confirmed event' },
    ],
  },
  happyRun: {
    label: 'happy run',
    outcome: 'committed',
    failureStep: null,
    compensationOrder: [],
    detail:
      'order-fulfillment: all 4 steps committed — nothing to undo, the saga is complete (4 forward steps, 0 compensations — the business operation completed)',
    entries: [
      { index: 0, phase: 'forward', step: 'reserve-item', outcome: 'done', evidence: 'stock widgets 2 -> 1 (held for the order)', at: 'T+1' },
      { index: 1, phase: 'forward', step: 'charge-card', outcome: 'done', evidence: 'balance 0 -> 4900 cents (charged)', at: 'T+2' },
      { index: 2, phase: 'forward', step: 'book-shipment', outcome: 'done', evidence: 'carrier slot held (1 of 2 free slots taken)', at: 'T+3' },
      { index: 3, phase: 'forward', step: 'announce-order', outcome: 'done', evidence: 'order-confirmed event 1 published', at: 'T+4' },
    ],
  },
  failureRun: {
    label: 'failing run (injected failure at book-shipment)',
    outcome: 'compensated',
    failureStep: 'book-shipment',
    compensationOrder: ['refund-card', 'release-item'],
    detail:
      'order-fulfillment: step book-shipment failed after 2 completed step(s) — 2 compensation(s) ran newest-first: refund-card then release-item (compensations ran newest-first: refund-card then release-item)',
    entries: [
      { index: 0, phase: 'forward', step: 'reserve-item', outcome: 'done', evidence: 'stock widgets 2 -> 1 (held for the order)', at: 'T+1' },
      { index: 1, phase: 'forward', step: 'charge-card', outcome: 'done', evidence: 'balance 0 -> 4900 cents (charged)', at: 'T+2' },
      { index: 2, phase: 'forward', step: 'book-shipment', outcome: 'failed', evidence: 'book-shipment failed: carrier full: no delivery slot until Thursday', at: 'T+3' },
      { index: 3, phase: 'compensate', step: 'refund-card', outcome: 'compensated', evidence: 'balance 4900 -> 0 cents (refunded)', at: 'T+4' },
      { index: 4, phase: 'compensate', step: 'release-item', outcome: 'compensated', evidence: 'stock widgets 1 -> 2 (hold released)', at: 'T+5' },
    ],
  },
  balances: [
    { metric: 'stock (widgets)', before: '2', afterHappy: '1', afterFailure: '2', verdict: 'held by the happy run, released by the undo — back to the start' },
    { metric: 'balance (cents)', before: '0', afterHappy: '4900', afterFailure: '0', verdict: 'charged, then refunded newest-first — net zero' },
  ],
  durability: [
    {
      half: 'the steps',
      what: 'each step is a message the outbox delivers at-least-once — a coordinator death re-delivers, the idempotent consumer dedupes',
      where: 'guide/domain/messaging/outbox_service.py (topic 22)',
    },
    {
      half: 'the run log',
      what: "the saga's own history is an event stream — a restarted coordinator reads its log forward and resumes where it stopped",
      where: 'guide/domain/patterns/event_store.py (this topic’s demo)',
    },
  ],
  honestyNote:
    'Both runs drove the real SagaCoordinator over a fresh scratch ledger on this request — the failure is an injected raise inside the step’s own effect, never a faked log.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<ArchSagaPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetArchSagaDemoUseCase, {
    saga: () => Promise.resolve(respond()),
  } as unknown as GetArchSagaDemoUseCase);
}

describe('ArchSagaDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['arch:saga']).toBeDefined();
  });

  it('renders both runs, the reversed undo, the balances, and the durability links', async () => {
    stubUseCase(() => success(fakePanel));

    render(<ArchSagaDemo />);

    await waitFor(() => expect(screen.getByTestId('asg-panel')).toBeInTheDocument());

    // The workflow: four steps, each naming its undo.
    expect(screen.getByTestId('asg-s-reserve-item')).toHaveTextContent('release-item');
    expect(screen.getByTestId('asg-s-announce-order')).toHaveTextContent('retract-announce');

    // The committed run: four forward entries.
    const happy = screen.getByTestId('asg-run-committed');
    expect(happy).toHaveTextContent('[committed]');
    expect(screen.getByTestId('asg-e-committed-announce-order')).toHaveTextContent(
      'order-confirmed event 1 published',
    );

    // The failing run: the failure, then the undo in REVERSE order.
    const failedRun = screen.getByTestId('asg-run-compensated');
    expect(failedRun).toHaveTextContent('[compensated]');
    expect(screen.getByTestId('asg-e-compensated-book-shipment')).toHaveTextContent('carrier full');
    expect(screen.getByTestId('asg-undo-order')).toHaveTextContent('refund-card -> release-item');
    expect(screen.getByTestId('asg-e-compensated-release-item')).toHaveTextContent(
      'stock widgets 1 -> 2',
    );

    // The balances: net zero after the undo.
    expect(screen.getByTestId('asg-b-stockwidgets')).toHaveTextContent('2 → 1 (happy) → 2 (failed)');
    expect(screen.getByTestId('asg-b-balancecents')).toHaveTextContent('net zero');

    // The durability links name both production halves.
    expect(screen.getByTestId('asg-d-the-steps')).toHaveTextContent('outbox');
    expect(screen.getByTestId('asg-d-the-run-log')).toHaveTextContent('event stream');

    expect(screen.getByTestId('asg-honesty-note')).toHaveTextContent('injected raise');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The saga panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-arch-saga-1',
            }),
          )
        : success(fakePanel);
    });

    render(<ArchSagaDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('asg-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
