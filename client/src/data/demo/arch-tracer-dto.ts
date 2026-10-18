import type {
  ArchBeat,
  ArchDependency,
  ArchFact,
  ArchHop,
  ArchRound,
  ArchRoute,
  ArchStackLayer,
  ArchTracerData,
  ArchWiring,
  BeatName,
  HopEvidence,
  ProviderKind,
  RoundOutcome,
  StackKind,
} from '../../domain/demo/arch-tracer';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * ArchTracerDTO — the wire/transport shape of the tracer payload. Mirrors
 * the domain model 1:1 (the interface is the seam where wire and domain
 * may diverge); the `fromJson` builds ONLY the listed fields (whitelist)
 * and throws on any shape violation, which parseDto upgrades to an
 * InvalidResponseException. Every field is always present on this
 * endpoint (no outcome-conditional omissions), so nulls are simply
 * invalid — per the family wire rule.
 */

export type ArchTracerDto = ArchTracerData;

const STACK_KINDS: readonly string[] = ['framework', 'user', 'router'];
const EVIDENCES: readonly string[] = ['measured', 'observed', 'introspected'];
const BEAT_EVENTS: readonly string[] = ['enter', 'response.start', 'complete'];
const OUTCOMES: readonly string[] = ['ok', 'err'];
const PROVIDER_KINDS: readonly string[] = ['model', 'function'];

/** Deserialize + validate the /api/demo/arch/tracer payload. */
export function archTracerDtoFromJson(body: unknown): ArchTracerDto {
  if (!isRecord(body)) throw new Error('arch tracer must be an object');
  return {
    stack: requiredArray(body, 'stack').map(stackLayerFromJson),
    route: routeFromJson(body['route']),
    wiring: wiringFromJson(body['wiring']),
    rounds: requiredArray(body, 'rounds').map(roundFromJson),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toArchTracer(dto: ArchTracerDto): ArchTracerData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function stackLayerFromJson(body: unknown): ArchStackLayer {
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

function dependencyFromJson(body: unknown): ArchDependency {
  if (!isRecord(body)) throw new Error('dependency must be an object');
  const providerKind = requiredString(body, 'providerKind');
  if (!PROVIDER_KINDS.includes(providerKind)) {
    throw new Error(`unknown provider kind "${providerKind}"`);
  }
  return {
    param: requiredString(body, 'param'),
    provider: requiredString(body, 'provider'),
    providerKind: providerKind as ProviderKind,
  };
}

function routeFromJson(body: unknown): ArchRoute {
  if (!isRecord(body)) throw new Error('route must be an object');
  return {
    template: requiredString(body, 'template'),
    method: requiredString(body, 'method'),
    endpoint: requiredString(body, 'endpoint'),
    responseModel: requiredString(body, 'responseModel'),
    dependencies: requiredArray(body, 'dependencies').map(dependencyFromJson),
  };
}

function wiringFromJson(body: unknown): ArchWiring {
  if (!isRecord(body)) throw new Error('wiring must be an object');
  return {
    port: requiredString(body, 'port'),
    adapter: requiredString(body, 'adapter'),
    useCases: requiredString(body, 'useCases'),
    wiredBy: requiredString(body, 'wiredBy'),
  };
}

function beatFromJson(body: unknown): ArchBeat {
  if (!isRecord(body)) throw new Error('beat must be an object');
  const event = requiredString(body, 'event');
  if (!BEAT_EVENTS.includes(event)) {
    throw new Error(`unknown beat event "${event}"`);
  }
  return {
    event: event as BeatName,
    offsetMs: requiredNumber(body, 'offsetMs'),
  };
}

function hopFromJson(body: unknown): ArchHop {
  if (!isRecord(body)) throw new Error('hop must be an object');
  const evidence = requiredString(body, 'evidence');
  if (!EVIDENCES.includes(evidence)) {
    throw new Error(`unknown hop evidence "${evidence}"`);
  }
  return {
    stage: requiredString(body, 'stage'),
    layer: requiredString(body, 'layer'),
    detail: requiredString(body, 'detail'),
    evidence: evidence as HopEvidence,
  };
}

function factFromJson(body: unknown): ArchFact {
  if (!isRecord(body)) throw new Error('fact must be an object');
  return {
    name: requiredString(body, 'name'),
    value: requiredString(body, 'value'),
  };
}

function roundFromJson(body: unknown): ArchRound {
  if (!isRecord(body)) throw new Error('round must be an object');
  const outcome = requiredString(body, 'outcome');
  if (!OUTCOMES.includes(outcome)) {
    throw new Error(`unknown round outcome "${outcome}"`);
  }
  return {
    outcome: outcome as RoundOutcome,
    requestLine: requiredString(body, 'requestLine'),
    inboundRequestId: requiredString(body, 'inboundRequestId'),
    status: requiredNumber(body, 'status'),
    beats: requiredArray(body, 'beats').map(beatFromJson),
    facts: requiredArray(body, 'facts').map(factFromJson),
    hops: requiredArray(body, 'hops').map(hopFromJson),
  };
}
