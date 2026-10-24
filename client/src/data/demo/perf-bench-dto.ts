import type {
  CompressionRow,
  GcCollectionRow,
  HealthAfter,
  HygieneRow,
  PerfBenchPanel,
  PerfFactRow,
} from '../../domain/demo/perf-bench';
import { isRecord, requiredArray, requiredBoolean, requiredNumber, requiredString } from '../content/validate';

/**
 * PerfBenchDTO — the wire/transport shape of the perf-bench panel. Every
 * field is always present on this payload (no nullables); numbers
 * validate as finite at the boundary so a drifted wire fails HERE, not
 * in a view.
 */

function compressionRowFromJson(value: unknown): CompressionRow {
  if (!isRecord(value)) throw new Error('compression row must be an object');
  return {
    payloadId: requiredString(value, 'payloadId'),
    payload: requiredString(value, 'payload'),
    level: requiredNumber(value, 'level'),
    rawBytes: requiredNumber(value, 'rawBytes'),
    gzippedBytes: requiredNumber(value, 'gzippedBytes'),
    savedPercent: requiredNumber(value, 'savedPercent'),
    encodeMs: requiredNumber(value, 'encodeMs'),
    decodeMs: requiredNumber(value, 'decodeMs'),
    iterations: requiredNumber(value, 'iterations'),
  };
}

function hygieneRowFromJson(value: unknown): HygieneRow {
  if (!isRecord(value)) throw new Error('hygiene row must be an object');
  return {
    label: requiredString(value, 'label'),
    what: requiredString(value, 'what'),
    elapsedMs: requiredNumber(value, 'elapsedMs'),
    loopLagMaxMs: requiredNumber(value, 'loopLagMaxMs'),
    concurrentHealthMs: requiredNumber(value, 'concurrentHealthMs'),
    concurrentHealthStatus: requiredNumber(value, 'concurrentHealthStatus'),
    verdict: requiredString(value, 'verdict'),
  };
}

function factRowFromJson(value: unknown): PerfFactRow {
  if (!isRecord(value)) throw new Error('fact row must be an object');
  return {
    id: requiredString(value, 'id'),
    label: requiredString(value, 'label'),
    value: requiredString(value, 'value'),
  };
}

function gcCollectionFromJson(value: unknown): GcCollectionRow {
  if (!isRecord(value)) throw new Error('gc collection must be an object');
  return {
    workload: requiredString(value, 'workload'),
    elapsedMs: requiredNumber(value, 'elapsedMs'),
    collected: requiredNumber(value, 'collected'),
    offLoop: requiredBoolean(value, 'offLoop'),
    note: requiredString(value, 'note'),
  };
}

function healthAfterFromJson(value: unknown): HealthAfter {
  if (!isRecord(value)) throw new Error('health after must be an object');
  return {
    status: requiredNumber(value, 'status'),
    elapsedMs: requiredNumber(value, 'elapsedMs'),
  };
}

/** Deserialize + validate the perf-bench panel (compression, hygiene, facts, GC, receipt). */
export function perfBenchPanelFromJson(body: unknown): PerfBenchPanel {
  if (!isRecord(body)) throw new Error('perf bench panel must be an object');
  return {
    compression: requiredArray(body, 'compression').map(compressionRowFromJson),
    hygiene: requiredArray(body, 'hygiene').map(hygieneRowFromJson),
    loop: requiredArray(body, 'loop').map(factRowFromJson),
    pool: requiredArray(body, 'pool').map(factRowFromJson),
    gcFacts: requiredArray(body, 'gcFacts').map(factRowFromJson),
    gcCollection: gcCollectionFromJson(body['gcCollection']),
    healthAfter: healthAfterFromJson(body['healthAfter']),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
