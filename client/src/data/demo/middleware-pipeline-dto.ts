import type {
  MiddlewarePipelineData,
  StackKind,
  StackLayer,
  TraceEvent,
  TracePhase,
} from '../../domain/demo/middleware-pipeline';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * MiddlewarePipelineDTO — the wire/transport shape of the pipeline payload.
 * Mirrors the domain model 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builds ONLY the listed fields
 * (whitelist) and throws on any shape violation, which parseDto upgrades
 * to an InvalidResponseException. Every field is always present on this
 * endpoint (no outcome-conditional omissions), so nulls are simply
 * invalid — per the family wire rule.
 */

export type MiddlewarePipelineDto = MiddlewarePipelineData;

const STACK_KINDS: readonly string[] = ['framework', 'user', 'router'];
const TRACE_PHASES: readonly string[] = ['request', 'handler', 'response'];

/** Deserialize + validate the /api/demo/middleware/pipeline payload. */
export function middlewarePipelineDtoFromJson(body: unknown): MiddlewarePipelineDto {
  if (!isRecord(body)) throw new Error('middleware pipeline must be an object');
  return {
    stack: requiredArray(body, 'stack').map(stackLayerFromJson),
    trace: requiredArray(body, 'trace').map(traceEventFromJson),
    requestSideOrder: requiredArray(body, 'requestSideOrder').map(nonEmptyString),
    responseSideOrder: requiredArray(body, 'responseSideOrder').map(nonEmptyString),
    requestId: requiredString(body, 'requestId'),
    requestIdHeader: requiredString(body, 'requestIdHeader'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toMiddlewarePipeline(dto: MiddlewarePipelineDto): MiddlewarePipelineData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function stackLayerFromJson(body: unknown): StackLayer {
  if (!isRecord(body)) throw new Error('stack layer must be an object');
  const kind = requiredString(body, 'kind');
  if (!STACK_KINDS.includes(kind)) {
    throw new Error(`unknown stack kind "${kind}"`);
  }
  return {
    name: requiredString(body, 'name'),
    kind: kind as StackKind,
    orderIndex: requiredNumber(body, 'orderIndex'),
    role: requiredString(body, 'role'),
  };
}

function traceEventFromJson(body: unknown): TraceEvent {
  if (!isRecord(body)) throw new Error('trace event must be an object');
  const phase = requiredString(body, 'phase');
  if (!TRACE_PHASES.includes(phase)) {
    throw new Error(`unknown trace phase "${phase}"`);
  }
  return {
    stage: requiredString(body, 'stage'),
    phase: phase as TracePhase,
    sequence: requiredNumber(body, 'sequence'),
    note: requiredString(body, 'note'),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('order entries must be non-empty strings');
  }
  return value;
}
