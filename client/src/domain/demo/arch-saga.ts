/**
 * Domain models for the advanced-architecture topic's saga panel (demo
 * block id `arch:saga`) — the client-side shape of
 * GET /api/demo/arch/saga. Field names match the server's camelCase
 * wire contract 1:1.
 *
 * The panel is the real SagaCoordinator's two lives over a scratch
 * ledger: the four-step order-fulfillment definition (every step
 * naming its compensation), a committed run, a failing run whose
 * compensations unwound the completed steps in REVERSE order with
 * per-step evidence, the balance rows proving the undo returned every
 * metric to its start, and the durability rows naming the two halves
 * (outbox delivery, the saga's own event stream) a production saga
 * adds around the in-process coordinator.
 */

/** One step of the saga's definition: a forward action and its undo, named. */
export interface SagaStepRow {
  action: string;
  compensates: string;
  describes: string;
}

/** The saga's definition — the document a reviewer reads before it runs. */
export interface SagaWorkflowRow {
  name: string;
  steps: SagaStepRow[];
}

/** One run-log line: direction, step, verdict, the effect's own evidence. */
export interface SagaEntryRow {
  index: number;
  phase: 'forward' | 'compensate';
  step: string;
  outcome: string;
  evidence: string;
  at: string;
}

/** One whole run: verdict, log, and (for the failing run) the undo proof. */
export interface SagaRunRow {
  label: string;
  outcome: 'committed' | 'compensated';
  failureStep: string | null;
  compensationOrder: string[];
  detail: string;
  entries: SagaEntryRow[];
}

/** One scratch-ledger metric across both runs — the undo's arithmetic. */
export interface SagaBalanceRow {
  metric: string;
  before: string;
  afterHappy: string;
  afterFailure: string;
  verdict: string;
}

/** One half of how a real saga survives crashes (the honest link). */
export interface SagaDurabilityRow {
  half: string;
  what: string;
  where: string;
}

/** Wire shape of GET /api/demo/arch/saga — both runs, the proof, the links. */
export interface ArchSagaPanel {
  workflow: SagaWorkflowRow;
  happyRun: SagaRunRow;
  failureRun: SagaRunRow;
  balances: SagaBalanceRow[];
  durability: SagaDurabilityRow[];
  honestyNote: string;
}
