import type {
  DepLifecycleEvent,
  DepLifecycleLogData,
  DepLifecycleSpanData,
} from '../../domain/demo/dep-lifecycle';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * DepLifecycleDTO — the wire/transport shape of the lifecycle payloads.
 * Mirrors the domain models 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builders construct ONLY the listed
 * fields (whitelist) and throw on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. The event union narrows on its
 * `event` discriminator exactly like the server's Literal.
 */

export type DepLifecycleSpanDto = DepLifecycleSpanData;
export type DepLifecycleLogDto = DepLifecycleLogData;

/** Deserialize + validate the GET /api/demo/dep/lifecycle payload. */
export function depLifecycleSpanDtoFromJson(body: unknown): DepLifecycleSpanDto {
  if (!isRecord(body)) throw new Error('lifecycle span must be an object');
  return {
    spanId: requiredString(body, 'spanId'),
    setupAt: requiredString(body, 'setupAt'),
    handlerOffsetMs: requiredNumber(body, 'handlerOffsetMs'),
    pendingEvents: requiredArray(body, 'pendingEvents').map(nonEmptyString),
  };
}

/** Deserialize + validate the GET /api/demo/dep/lifecycle/log payload. */
export function depLifecycleLogDtoFromJson(body: unknown): DepLifecycleLogDto {
  if (!isRecord(body)) throw new Error('lifecycle log must be an object');
  return {
    capacity: requiredNumber(body, 'capacity'),
    events: requiredArray(body, 'events').map(eventFromJson),
  };
}

/** Convert the transport DTOs into domain models (identity while 1:1). */
export function toDepLifecycleSpan(dto: DepLifecycleSpanDto): DepLifecycleSpanData {
  return dto;
}

/** Convert the log DTO into its domain model (identity while 1:1). */
export function toDepLifecycleLog(dto: DepLifecycleLogDto): DepLifecycleLogData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function eventFromJson(body: unknown): DepLifecycleEvent {
  if (!isRecord(body)) throw new Error('span event must be an object');
  const event = requiredString(body, 'event');
  switch (event) {
    case 'setup':
    case 'handler':
    case 'response':
    case 'teardown':
      return {
        sequence: requiredNumber(body, 'sequence'),
        spanId: requiredString(body, 'spanId'),
        event,
        at: requiredString(body, 'at'),
        offsetMs: requiredNumber(body, 'offsetMs'),
      };
    default:
      throw new Error(`unknown span event "${event}"`);
  }
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('pending event entries must be non-empty strings');
  }
  return value;
}
