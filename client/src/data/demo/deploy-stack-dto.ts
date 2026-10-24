import type {
  DeployStackPanel,
  RuntimeRow,
  StackAreaRow,
  StackCheckKind,
  StackItemRow,
  StackVerdict,
} from '../../domain/demo/deploy-stack';
import { isRecord, optionalString, requiredArray, requiredString } from '../content/validate';

/**
 * DeployStackDTO — the wire/transport shape of the deploy-stack panel.
 * Every field is always present on this payload (no nullables) except
 * whyManual, which exists exactly on manual rows and claims nothing
 * elsewhere; checkKind and verdict validate against their literal unions
 * at the boundary so a drifted wire fails HERE, not in a view.
 */

const CHECK_KINDS: readonly StackCheckKind[] = ['live', 'file', 'manual'];
const VERDICTS: readonly StackVerdict[] = ['pass', 'fail', 'manual'];

function oneOf<T extends string>(value: unknown, allowed: readonly T[], what: string): T {
  if (typeof value !== 'string' || !allowed.includes(value as T)) {
    throw new Error(`${what} must be one of ${allowed.join('/')} — got ${String(value)}`);
  }
  return value as T;
}

function runtimeRowFromJson(value: unknown): RuntimeRow {
  if (!isRecord(value)) throw new Error('runtime row must be an object');
  return {
    id: requiredString(value, 'id'),
    label: requiredString(value, 'label'),
    value: requiredString(value, 'value'),
  };
}

function stackItemFromJson(value: unknown): StackItemRow {
  if (!isRecord(value)) throw new Error('stack item must be an object');
  return {
    id: requiredString(value, 'id'),
    claim: requiredString(value, 'claim'),
    checkKind: oneOf(value['checkKind'], CHECK_KINDS, 'stack item checkKind'),
    verdict: oneOf(value['verdict'], VERDICTS, 'stack item verdict'),
    evidence: requiredArray(value, 'evidence').map((line) => {
      if (typeof line !== 'string') throw new Error('stack item evidence must be strings');
      return line;
    }),
    whyManual: optionalString(value, 'whyManual'),
  };
}

function stackAreaFromJson(value: unknown): StackAreaRow {
  if (!isRecord(value)) throw new Error('stack area must be an object');
  return {
    id: requiredString(value, 'id'),
    title: requiredString(value, 'title'),
    note: requiredString(value, 'note'),
    items: requiredArray(value, 'items').map(stackItemFromJson),
  };
}

/** Deserialize + validate the deploy-stack panel (runtime facts, areas, rows). */
export function deployStackPanelFromJson(body: unknown): DeployStackPanel {
  if (!isRecord(body)) throw new Error('deploy stack panel must be an object');
  return {
    runtime: requiredArray(body, 'runtime').map(runtimeRowFromJson),
    areas: requiredArray(body, 'areas').map(stackAreaFromJson),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
