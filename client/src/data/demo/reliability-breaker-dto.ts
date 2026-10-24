import type { BreakerCallRow, BreakerFactRow, BreakerPanel } from '../../domain/demo/reliability-breaker';
import { isRecord, requiredArray, requiredBoolean, requiredNumber, requiredString } from '../content/validate';

/**
 * ReliabilityBreakerDTO — the wire/transport shape of the breaker panel.
 * Every field is always present on this payload; the two genuinely
 * nullable ones (`admitted`, `retryAfterS`) validate as boolean-or-null /
 * number-or-null at the boundary so a drifted wire fails HERE, not in a
 * view.
 */

function nullableBoolean(source: Record<string, unknown>, key: string): boolean | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value === 'boolean') return value;
  throw new Error(`expected boolean or null for ${key}`);
}

function nullableNumber(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  throw new Error(`expected finite number or null for ${key}`);
}

function factRowFromJson(value: unknown): BreakerFactRow {
  if (!isRecord(value)) throw new Error('breaker fact row must be an object');
  return {
    id: requiredString(value, 'id'),
    label: requiredString(value, 'label'),
    value: requiredString(value, 'value'),
  };
}

function callRowFromJson(value: unknown): BreakerCallRow {
  if (!isRecord(value)) throw new Error('breaker call row must be an object');
  return {
    step: requiredNumber(value, 'step'),
    label: requiredString(value, 'label'),
    action: requiredString(value, 'action'),
    stateBefore: requiredString(value, 'stateBefore'),
    admitted: nullableBoolean(value, 'admitted'),
    isProbe: requiredBoolean(value, 'isProbe'),
    dependencyTouched: requiredBoolean(value, 'dependencyTouched'),
    outcome: requiredString(value, 'outcome'),
    elapsedMs: requiredNumber(value, 'elapsedMs'),
    consecutiveFailures: requiredNumber(value, 'consecutiveFailures'),
    retryAfterS: nullableNumber(value, 'retryAfterS'),
    reason: requiredString(value, 'reason'),
  };
}

/** Deserialize + validate the breaker panel (policy, walk, latency, cycle line). */
export function breakerPanelFromJson(body: unknown): BreakerPanel {
  if (!isRecord(body)) throw new Error('breaker panel must be an object');
  return {
    policy: requiredArray(body, 'policy').map(factRowFromJson),
    calls: requiredArray(body, 'calls').map(callRowFromJson),
    latency: requiredArray(body, 'latency').map(factRowFromJson),
    statesVisited: requiredArray(body, 'statesVisited').map((state) => {
      if (typeof state !== 'string') throw new Error('statesVisited entries must be strings');
      return state;
    }),
    stateLine: requiredString(body, 'stateLine'),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
