import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, type StubRoute } from '../../test/fetch_stub';
import { ArchSagaApi } from './arch-saga-api';
import { ArchSagaRepositoryImpl } from './arch-saga-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * ArchSagaRepositoryImpl spec — the fixture below is a VERBATIM capture
 * of the real wire payload (GET /api/demo/arch/saga, captured 2026-10-25
 * from the running dev stack; the builder is deterministic, pinned by a
 * server test), so every run of this suite parses the DTO's fromJson
 * against the payload the server actually serves — the wire-drift pin.
 * The happy run's `failureStep` is genuinely `null` on the wire (a
 * committed run has no failed step); an optional-string validator once
 * rejected that null and the panel died with invalid_response on a 200.
 * A drifted DTO must fail HERE, never in the browser.
 */

const capturedPanel = {
  workflow: {
    name: 'order-fulfillment',
    steps: [
      {
        action: 'reserve-item',
        compensates: 'release-item',
        describes: 'hold one unit of stock locally (a real transaction)',
      },
      {
        action: 'charge-card',
        compensates: 'refund-card',
        describes: 'take payment at the payment service',
      },
      {
        action: 'book-shipment',
        compensates: 'cancel-shipment',
        describes: 'reserve a delivery slot at the carrier',
      },
      {
        action: 'announce-order',
        compensates: 'retract-announce',
        describes: 'publish the order-confirmed event',
      },
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
      {
        index: 0,
        phase: 'forward',
        step: 'reserve-item',
        outcome: 'done',
        evidence: 'stock widgets 2 -> 1 (held for the order)',
        at: 'T+1',
      },
      {
        index: 1,
        phase: 'forward',
        step: 'charge-card',
        outcome: 'done',
        evidence: 'balance 0 -> 4900 cents (charged)',
        at: 'T+2',
      },
      {
        index: 2,
        phase: 'forward',
        step: 'book-shipment',
        outcome: 'done',
        evidence: 'carrier slot held (1 of 2 free slots taken)',
        at: 'T+3',
      },
      {
        index: 3,
        phase: 'forward',
        step: 'announce-order',
        outcome: 'done',
        evidence: 'order-confirmed event 1 published',
        at: 'T+4',
      },
    ],
  },
  failureRun: {
    label: 'failing run (injected failure at book-shipment)',
    outcome: 'compensated',
    failureStep: 'book-shipment',
    compensationOrder: ['refund-card', 'release-item'],
    detail:
      "order-fulfillment: step 'book-shipment' failed after 2 completed step(s) — 2 compensation(s) ran newest-first: refund-card then release-item (compensations ran newest-first: refund-card then release-item)",
    entries: [
      {
        index: 0,
        phase: 'forward',
        step: 'reserve-item',
        outcome: 'done',
        evidence: 'stock widgets 2 -> 1 (held for the order)',
        at: 'T+1',
      },
      {
        index: 1,
        phase: 'forward',
        step: 'charge-card',
        outcome: 'done',
        evidence: 'balance 0 -> 4900 cents (charged)',
        at: 'T+2',
      },
      {
        index: 2,
        phase: 'forward',
        step: 'book-shipment',
        outcome: 'failed',
        evidence: 'book-shipment failed: carrier full: no delivery slot until Thursday',
        at: 'T+3',
      },
      {
        index: 3,
        phase: 'compensate',
        step: 'refund-card',
        outcome: 'compensated',
        evidence: 'balance 4900 -> 0 cents (refunded)',
        at: 'T+4',
      },
      {
        index: 4,
        phase: 'compensate',
        step: 'release-item',
        outcome: 'compensated',
        evidence: 'stock widgets 1 -> 2 (hold released)',
        at: 'T+5',
      },
    ],
  },
  balances: [
    {
      metric: 'stock (widgets)',
      before: '2',
      afterHappy: '1',
      afterFailure: '2',
      verdict: 'held by the happy run, released by the undo — back to the start',
    },
    {
      metric: 'balance (cents)',
      before: '0',
      afterHappy: '4900',
      afterFailure: '0',
      verdict: 'charged, then refunded newest-first — net zero',
    },
    {
      metric: 'carrier slots held',
      before: '0',
      afterHappy: '1',
      afterFailure: '0',
      verdict: 'the failing step never wrote — nothing to undo for it',
    },
    {
      metric: 'announcements',
      before: '0',
      afterHappy: '1',
      afterFailure: '0',
      verdict: 'the fourth step never ran — the run stopped at the failure',
    },
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
      where: 'guide/domain/patterns/event_store.py (this topic\u2019s demo)',
    },
  ],
  honestyNote:
    'Both runs drove the real SagaCoordinator over a fresh scratch ledger on this request — the failure is an injected raise inside the step\u2019s own effect, never a faked log. This panel is the pattern\u2019s decision core in-process; a production saga adds the outbox\u2019s durability (see the durability rows) around exactly this coordinator.',
};

const sagaRoute: StubRoute = {
  url: '/api/demo/arch/saga',
  body: capturedPanel,
};

function makeRepository(): ArchSagaRepositoryImpl {
  return new ArchSagaRepositoryImpl(new ArchSagaApi(createAppConfig()));
}

describe('ArchSagaRepositoryImpl', () => {
  it('round-trips the captured REAL wire payload (the wire-drift pin)', async () => {
    stubApiFetch([sagaRoute]);
    const result = await makeRepository().saga();
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    // THE field that once drifted: the committed run's failureStep is
    // null ON THE WIRE and must survive the DTO as null.
    expect(result.value.happyRun.failureStep).toBeNull();
    expect(result.value.failureRun.failureStep).toBe('book-shipment');
    expect(result.value.workflow.steps).toHaveLength(4);
    expect(result.value.happyRun.entries).toHaveLength(4);
    expect(result.value.failureRun.entries).toHaveLength(5);
    expect(result.value.failureRun.compensationOrder).toEqual(['refund-card', 'release-item']);
    expect(result.value.balances).toHaveLength(4);
    expect(result.value.honestyNote).toContain('real SagaCoordinator');
  });

  it('resolves a drifted wire as a Failed invalid_response Result, never throws', async () => {
    const drifted = JSON.parse(JSON.stringify(capturedPanel)) as {
      happyRun: { failureStep: unknown };
    };
    drifted.happyRun.failureStep = 7;
    stubApiFetch([{ url: '/api/demo/arch/saga', body: drifted }]);

    const result = await makeRepository().saga();
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.failure.code).toBe('invalid_response');
  });
});
