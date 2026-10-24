import type {
  ArchSagaPanel,
  SagaBalanceRow,
  SagaDurabilityRow,
  SagaEntryRow,
  SagaRunRow,
  SagaStepRow,
  SagaWorkflowRow,
} from '../../domain/demo/arch-saga';
import { isRecord, optionalString, requiredArray, requiredNumber, requiredString } from '../content/validate';

/**
 * ArchSagaDTO — the wire/transport shape of the saga panel. Every
 * field is always present on this payload; validation happens at the
 * boundary so a drifted wire fails HERE, not in a view.
 */

function stepRowFromJson(value: unknown): SagaStepRow {
  if (!isRecord(value)) throw new Error('saga step row must be an object');
  return {
    action: requiredString(value, 'action'),
    compensates: requiredString(value, 'compensates'),
    describes: requiredString(value, 'describes'),
  };
}

function workflowRowFromJson(value: unknown): SagaWorkflowRow {
  if (!isRecord(value)) throw new Error('saga workflow must be an object');
  return {
    name: requiredString(value, 'name'),
    steps: requiredArray(value, 'steps').map(stepRowFromJson),
  };
}

function entryRowFromJson(value: unknown): SagaEntryRow {
  if (!isRecord(value)) throw new Error('saga entry row must be an object');
  const phase = requiredString(value, 'phase');
  if (phase !== 'forward' && phase !== 'compensate') {
    throw new Error(`saga entry phase must be forward|compensate, got ${phase}`);
  }
  return {
    index: requiredNumber(value, 'index'),
    phase,
    step: requiredString(value, 'step'),
    outcome: requiredString(value, 'outcome'),
    evidence: requiredString(value, 'evidence'),
    at: requiredString(value, 'at'),
  };
}

function runRowFromJson(value: unknown): SagaRunRow {
  if (!isRecord(value)) throw new Error('saga run row must be an object');
  const outcome = requiredString(value, 'outcome');
  if (outcome !== 'committed' && outcome !== 'compensated') {
    throw new Error(`saga run outcome must be committed|compensated, got ${outcome}`);
  }
  const failureStep = optionalString(value, 'failureStep');
  return {
    label: requiredString(value, 'label'),
    outcome,
    failureStep: failureStep ?? null,
    compensationOrder: requiredArray(value, 'compensationOrder').map((item) => {
      if (typeof item !== 'string') throw new Error('compensationOrder entries must be strings');
      return item;
    }),
    detail: requiredString(value, 'detail'),
    entries: requiredArray(value, 'entries').map(entryRowFromJson),
  };
}

function balanceRowFromJson(value: unknown): SagaBalanceRow {
  if (!isRecord(value)) throw new Error('saga balance row must be an object');
  return {
    metric: requiredString(value, 'metric'),
    before: requiredString(value, 'before'),
    afterHappy: requiredString(value, 'afterHappy'),
    afterFailure: requiredString(value, 'afterFailure'),
    verdict: requiredString(value, 'verdict'),
  };
}

function durabilityRowFromJson(value: unknown): SagaDurabilityRow {
  if (!isRecord(value)) throw new Error('saga durability row must be an object');
  return {
    half: requiredString(value, 'half'),
    what: requiredString(value, 'what'),
    where: requiredString(value, 'where'),
  };
}

/** Deserialize + validate the saga panel (workflow..durability, note). */
export function archSagaPanelFromJson(body: unknown): ArchSagaPanel {
  if (!isRecord(body)) throw new Error('arch saga panel must be an object');
  return {
    workflow: workflowRowFromJson(body['workflow']),
    happyRun: runRowFromJson(body['happyRun']),
    failureRun: runRowFromJson(body['failureRun']),
    balances: requiredArray(body, 'balances').map(balanceRowFromJson),
    durability: requiredArray(body, 'durability').map(durabilityRowFromJson),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
