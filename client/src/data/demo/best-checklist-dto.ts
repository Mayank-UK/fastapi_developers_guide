import type {
  BestChecklistPanel,
  CheckKind,
  ChecklistAreaRow,
  ChecklistItemRow,
  ChecklistSummaryRow,
  NotDoneRow,
  Verdict,
} from '../../domain/demo/best-checklist';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
  requiredText,
} from '../content/validate';

/**
 * BestChecklistDTO — the wire/transport shapes of the best-practices
 * self-audit. Like every DTO constructor here it whitelists keys and
 * throws on shape violations, so hostile or drifted payloads surface
 * loudly instead of reaching the domain half-parsed. An empty evidence
 * list is DATA (manual rows carry none by design), never absence.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function checkKind(value: unknown): CheckKind {
  if (value !== 'live' && value !== 'file' && value !== 'manual') {
    throw new Error(`unknown check kind: ${String(value)}`);
  }
  return value;
}

function verdict(value: unknown): Verdict {
  if (value !== 'pass' && value !== 'fail' && value !== 'manual') {
    throw new Error(`unknown verdict: ${String(value)}`);
  }
  return value;
}

function itemRowFromJson(value: unknown): ChecklistItemRow {
  if (!isRecord(value)) throw new Error('checklist item must be an object');
  return {
    id: requiredString(value, 'id'),
    practice: requiredString(value, 'practice'),
    checkKind: checkKind(value['checkKind']),
    verdict: verdict(value['verdict']),
    evidence: requiredArray(value, 'evidence').map((entry) => {
      if (typeof entry !== 'string') throw new Error('evidence entries must be strings');
      return entry;
    }),
    whyManual: stringOrNull(value, 'whyManual'),
  };
}

function areaRowFromJson(value: unknown): ChecklistAreaRow {
  if (!isRecord(value)) throw new Error('checklist area must be an object');
  return {
    id: requiredString(value, 'id'),
    title: requiredString(value, 'title'),
    note: requiredString(value, 'note'),
    items: requiredArray(value, 'items').map(itemRowFromJson),
  };
}

function notDoneFromJson(value: unknown): NotDoneRow {
  if (!isRecord(value)) throw new Error('not-done row must be an object');
  return {
    id: requiredString(value, 'id'),
    notDone: requiredString(value, 'notDone'),
    reason: requiredText(value, 'reason'),
    artifacts: requiredArray(value, 'artifacts').map((entry) => {
      if (typeof entry !== 'string') throw new Error('artifacts must be strings');
      return entry;
    }),
  };
}

function summaryFromJson(value: unknown): ChecklistSummaryRow {
  if (!isRecord(value)) throw new Error('checklist summary must be an object');
  return {
    items: requiredNumber(value, 'items'),
    passed: requiredNumber(value, 'passed'),
    failed: requiredNumber(value, 'failed'),
    manual: requiredNumber(value, 'manual'),
  };
}

/** Deserialize + validate the self-audit panel. */
export function bestChecklistPanelFromJson(body: unknown): BestChecklistPanel {
  if (!isRecord(body)) throw new Error('best checklist panel must be an object');
  return {
    areas: requiredArray(body, 'areas').map(areaRowFromJson),
    notDones: requiredArray(body, 'notDones').map(notDoneFromJson),
    summary: summaryFromJson(body['summary']),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
