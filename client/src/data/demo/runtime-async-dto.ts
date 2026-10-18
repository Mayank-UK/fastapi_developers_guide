import type {
  IoTask,
  RuntimeAsyncDemoData,
  TaskTiming,
  TimingRun,
  TraceEvent,
} from '../../domain/demo/runtime-async';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * RuntimeAsyncDTO — the wire/transport shape of the async-timing demo
 * payload. Mirrors the domain model 1:1 (the interface is the seam where
 * wire and domain may diverge); the `fromJson` builds ONLY the listed
 * fields (whitelist) and throws on any shape violation, which parseDto
 * upgrades to an InvalidResponseException.
 */

export type RuntimeAsyncDemoDto = RuntimeAsyncDemoData;

/** Deserialize + validate the GET /api/demo/runtime/async payload. */
export function runtimeAsyncDtoFromJson(body: unknown): RuntimeAsyncDemoDto {
  if (!isRecord(body)) throw new Error('runtime-async payload must be an object');
  return {
    ioPlan: requiredArray(body, 'ioPlan').map(ioTaskFromJson),
    sequential: timingRunFromJson(body.sequential, 'sequential'),
    gathered: timingRunFromJson(body.gathered, 'gathered'),
    speedup: requiredNumber(body, 'speedup'),
    trace: requiredArray(body, 'trace').map(traceEventFromJson),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toRuntimeAsyncDemo(dto: RuntimeAsyncDemoDto): RuntimeAsyncDemoData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function ioTaskFromJson(body: unknown): IoTask {
  if (!isRecord(body)) throw new Error('io task must be an object');
  return {
    name: requiredString(body, 'name'),
    simulatedIoMs: requiredNumber(body, 'simulatedIoMs'),
  };
}

function timingRunFromJson(body: unknown, expected: TimingRun['strategy']): TimingRun {
  if (!isRecord(body)) throw new Error(`timing run "${expected}" must be an object`);
  const strategy = requiredString(body, 'strategy');
  if (strategy !== expected) {
    throw new Error(`timing run strategy "${strategy}" does not match "${expected}"`);
  }
  return {
    strategy,
    elapsedMs: requiredNumber(body, 'elapsedMs'),
    completionOrder: requiredArray(body, 'completionOrder').map(requiredStringShallow),
    perTask: requiredArray(body, 'perTask').map(taskTimingFromJson),
  };
}

function taskTimingFromJson(body: unknown): TaskTiming {
  if (!isRecord(body)) throw new Error('task timing must be an object');
  return {
    name: requiredString(body, 'name'),
    simulatedIoMs: requiredNumber(body, 'simulatedIoMs'),
    measuredMs: requiredNumber(body, 'measuredMs'),
  };
}

function traceEventFromJson(body: unknown): TraceEvent {
  if (!isRecord(body)) throw new Error('trace event must be an object');
  return {
    actor: requiredString(body, 'actor'),
    event: requiredString(body, 'event'),
  };
}

function requiredStringShallow(body: unknown): string {
  if (typeof body !== 'string' || body === '') {
    throw new Error('completion order entries must be non-empty strings');
  }
  return body;
}
