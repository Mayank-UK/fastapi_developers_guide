import type {
  ConsumeMode,
  ConsumeOutcome,
  PendingEntry,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamEntry,
  StreamPanel,
} from '../../domain/demo/msg-stream';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * MsgStreamDTO — the wire/transport shapes of the stream lab: the roster
 * panel plus the four action outcomes. The server's vocabularies are
 * closed (modes, event types), so unknown values fail validation here
 * rather than rendering as lies.
 */

const MODES = ['healthy', 'poison'] as const;

/** Parse one consume persona; the server's vocabulary is closed. */
export function consumeModeFromJson(value: unknown): ConsumeMode {
  if (typeof value !== 'string') throw new Error('consume mode must be a string');
  if (!MODES.includes(value as (typeof MODES)[number])) {
    throw new Error(`unknown consume mode: ${value}`);
  }
  return value as ConsumeMode;
}

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  // null rides the wire when there is nothing to report (no last id yet);
  // the DTO treats it as absent-on-purpose, never as a bad field.
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

export function entryFromJson(value: unknown): StreamEntry {
  if (!isRecord(value)) throw new Error('stream entry must be an object');
  return {
    id: requiredString(value, 'id'),
    eventId: requiredString(value, 'eventId'),
    eventType: requiredString(value, 'eventType'),
    payload: requiredString(value, 'payload'),
  };
}

function pendingEntryFromJson(value: unknown): PendingEntry {
  if (!isRecord(value)) throw new Error('pending entry must be an object');
  return {
    entryId: requiredString(value, 'entryId'),
    consumer: requiredString(value, 'consumer'),
    idleMs: requiredNumber(value, 'idleMs'),
    deliveries: requiredNumber(value, 'deliveries'),
  };
}

/** Deserialize + validate the roster payload. */
export function streamPanelFromJson(body: unknown): StreamPanel {
  if (!isRecord(body)) throw new Error('stream panel must be an object');
  return {
    namespace: requiredString(body, 'namespace'),
    stream: requiredString(body, 'stream'),
    group: requiredString(body, 'group'),
    healthyConsumer: requiredString(body, 'healthyConsumer'),
    poisonConsumer: requiredString(body, 'poisonConsumer'),
    length: requiredNumber(body, 'length'),
    displayed: requiredNumber(body, 'displayed'),
    lastId: stringOrNull(body, 'lastId'),
    entries: requiredArray(body, 'entries').map(entryFromJson),
    pendingCount: requiredNumber(body, 'pendingCount'),
    produceEndpoint: requiredString(body, 'produceEndpoint'),
    consumeEndpoint: requiredString(body, 'consumeEndpoint'),
    pendingEndpoint: requiredString(body, 'pendingEndpoint'),
    reclaimEndpoint: requiredString(body, 'reclaimEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the produce outcome. */
export function produceFromJson(body: unknown): ProduceOutcome {
  if (!isRecord(body)) throw new Error('produce outcome must be an object');
  return {
    stream: requiredString(body, 'stream'),
    eventId: requiredString(body, 'eventId'),
    entryId: requiredString(body, 'entryId'),
    note: requiredString(body, 'note'),
    length: requiredNumber(body, 'length'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the consume outcome. */
export function consumeFromJson(body: unknown): ConsumeOutcome {
  if (!isRecord(body)) throw new Error('consume outcome must be an object');
  return {
    stream: requiredString(body, 'stream'),
    group: requiredString(body, 'group'),
    consumer: requiredString(body, 'consumer'),
    mode: consumeModeFromJson(body['mode']),
    delivered: requiredArray(body, 'delivered').map(entryFromJson),
    acked: requiredNumber(body, 'acked'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the pending list outcome. */
export function pendingListFromJson(body: unknown): PendingListOutcome {
  if (!isRecord(body)) throw new Error('pending list must be an object');
  return {
    stream: requiredString(body, 'stream'),
    group: requiredString(body, 'group'),
    entries: requiredArray(body, 'entries').map(pendingEntryFromJson),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the reclaim outcome. */
export function reclaimFromJson(body: unknown): ReclaimOutcome {
  if (!isRecord(body)) throw new Error('reclaim outcome must be an object');
  return {
    stream: requiredString(body, 'stream'),
    group: requiredString(body, 'group'),
    consumer: requiredString(body, 'consumer'),
    minIdleMs: requiredNumber(body, 'minIdleMs'),
    claimed: requiredArray(body, 'claimed').map(entryFromJson),
    acked: requiredNumber(body, 'acked'),
    detail: requiredString(body, 'detail'),
  };
}
