import {
  type SampleRun,
  type Uuid7Layout,
  type UuidLab,
  type UuidSegment,
  type UuidStrategy,
} from '../../domain/demo/uuid-lab';
import {
  isRecord,
  optionalNumber,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * UuidLabDTO — the wire/transport shapes of the UUID lab. Mirrors the
 * domain models 1:1; the `fromJson` builders construct ONLY the listed
 * fields (whitelist) and throw on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. `randomBits` is an optional
 * wire field (0 is data for the sequence — the server sends 0 — and
 * undefined only if absent, which is a violation of the lab's own
 * contract, but tolerated as an honest optional).
 */

export type UuidLabDto = UuidLab;

function runFromJson(body: unknown): SampleRun {
  if (!isRecord(body)) throw new Error('sample run must be an object');
  return {
    kind: requiredString(body, 'kind') as SampleRun['kind'],
    values: requiredArray(body, 'values').map((v, i) => {
      if (typeof v !== 'string' || v === '') {
        throw new Error(`expected non-empty string at values[${i}]`);
      }
      return v;
    }),
    sortRanks: requiredArray(body, 'sortRanks').map((r, i) => {
      if (typeof r !== 'number' || !Number.isInteger(r) || r < 0) {
        throw new Error(`expected non-negative integer at sortRanks[${i}]`);
      }
      return r;
    }),
    sortable: requiredBoolean(body, 'sortable'),
  };
}

function segmentFromJson(body: unknown): UuidSegment {
  if (!isRecord(body)) throw new Error('uuid segment must be an object');
  return {
    label: requiredString(body, 'label'),
    hexValue: requiredString(body, 'hexValue'),
    bits: requiredNumber(body, 'bits'),
    meaning: requiredString(body, 'meaning'),
  };
}

function layoutFromJson(body: unknown): Uuid7Layout {
  if (!isRecord(body)) throw new Error('uuid7 layout must be an object');
  return {
    value: requiredString(body, 'value'),
    unixMs: requiredNumber(body, 'unixMs'),
    generatedAtIso: requiredString(body, 'generatedAtIso'),
    segments: requiredArray(body, 'segments').map(segmentFromJson),
  };
}

function strategyFromJson(body: unknown): UuidStrategy {
  if (!isRecord(body)) throw new Error('uuid strategy must be an object');
  const randomBits = optionalNumber(body, 'randomBits');
  return {
    id: requiredString(body, 'id'),
    name: requiredString(body, 'name'),
    sortableAsText: requiredBoolean(body, 'sortableAsText'),
    indexLocality: requiredString(body, 'indexLocality'),
    coordination: requiredString(body, 'coordination'),
    leaksTiming: requiredBoolean(body, 'leaksTiming'),
    ...(randomBits === undefined ? {} : { randomBits }),
  };
}

/** Deserialize + validate the whole lab payload. */
export function uuidLabFromJson(body: unknown): UuidLabDto {
  if (!isRecord(body)) throw new Error('uuid lab must be an object');
  return {
    sampleCount: requiredNumber(body, 'sampleCount'),
    runs: requiredArray(body, 'runs').map(runFromJson),
    sharedPrefixHex: requiredString(body, 'sharedPrefixHex'),
    layout: layoutFromJson(body.layout),
    strategies: requiredArray(body, 'strategies').map(strategyFromJson),
    reasoning: requiredString(body, 'reasoning'),
  };
}
