import type {
  OutboxConsumeOutcome,
  OutboxPanel,
  OutboxPostRow,
  OutboxRow,
  OutboxWriteOutcome,
  PublishedEntry,
  RelayOutcome,
} from '../../domain/demo/msg-outbox';
import { entryFromJson } from './msg-stream-dto';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * MsgOutboxDTO — the wire/transport shapes of the outbox lab: the roster
 * payload plus the three action outcomes. Optional halves (post, event,
 * failure) ride the wire as null when absent-on-purpose; the DTO treats
 * those nulls as honest absence, never as a bad field.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function outboxRowFromJson(value: unknown): OutboxRow {
  if (!isRecord(value)) throw new Error('outbox row must be an object');
  return {
    eventId: requiredString(value, 'eventId'),
    eventType: requiredString(value, 'eventType'),
    aggregate: requiredString(value, 'aggregate'),
    payload: requiredString(value, 'payload'),
    createdAt: requiredString(value, 'createdAt'),
    publishedAt: stringOrNull(value, 'publishedAt'),
  };
}

function postRowFromJson(value: unknown): OutboxPostRow {
  if (!isRecord(value)) throw new Error('outbox post row must be an object');
  return {
    id: requiredNumber(value, 'id'),
    slug: requiredString(value, 'slug'),
    title: requiredString(value, 'title'),
    author: requiredString(value, 'author'),
    createdAt: requiredString(value, 'createdAt'),
  };
}

/** Deserialize + validate the roster payload. */
export function outboxPanelFromJson(body: unknown): OutboxPanel {
  if (!isRecord(body)) throw new Error('outbox panel must be an object');
  const stats = requiredRecord(body, 'stats');
  const telemetry = requiredRecord(body, 'telemetry');
  return {
    namespace: requiredString(body, 'namespace'),
    stream: requiredString(body, 'stream'),
    table: requiredString(body, 'table'),
    stats: {
      total: requiredNumber(stats, 'total'),
      published: requiredNumber(stats, 'published'),
      unpublished: requiredNumber(stats, 'unpublished'),
    },
    outbox: requiredArray(body, 'outbox').map(outboxRowFromJson),
    streamEntries: requiredArray(body, 'streamEntries').map(entryFromJson),
    telemetry: {
      creates: requiredNumber(telemetry, 'creates'),
      relayCycles: requiredNumber(telemetry, 'relayCycles'),
      crashSimulations: requiredNumber(telemetry, 'crashSimulations'),
      publishes: requiredNumber(telemetry, 'publishes'),
      eventsProcessed: requiredNumber(telemetry, 'eventsProcessed'),
      duplicatesSkipped: requiredNumber(telemetry, 'duplicatesSkipped'),
    },
    postsEndpoint: requiredString(body, 'postsEndpoint'),
    relayEndpoint: requiredString(body, 'relayEndpoint'),
    consumeEndpoint: requiredString(body, 'consumeEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the one-transaction write outcome. */
export function outboxWriteFromJson(body: unknown): OutboxWriteOutcome {
  if (!isRecord(body)) throw new Error('outbox write outcome must be an object');
  const post = body['post'];
  const event = body['event'];
  return {
    committed: body['committed'] === true,
    post: post === null || post === undefined ? null : postRowFromJson(post),
    event: event === null || event === undefined ? null : outboxRowFromJson(event),
    failure: stringOrNull(body, 'failure'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the relay outcome. */
export function relayFromJson(body: unknown): RelayOutcome {
  if (!isRecord(body)) throw new Error('relay outcome must be an object');
  const published = requiredArray(body, 'published');
  return {
    cycle: requiredNumber(body, 'cycle'),
    stream: requiredString(body, 'stream'),
    discovered: requiredNumber(body, 'discovered'),
    published: published.map((value) => {
      if (!isRecord(value)) throw new Error('published entry must be an object');
      const entry: PublishedEntry = {
        eventId: requiredString(value, 'eventId'),
        entryId: requiredString(value, 'entryId'),
        aggregate: requiredString(value, 'aggregate'),
      };
      return entry;
    }),
    marked: requiredNumber(body, 'marked'),
    crashed: body['crashed'] === true,
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the idempotent consume outcome. */
export function outboxConsumeFromJson(body: unknown): OutboxConsumeOutcome {
  if (!isRecord(body)) throw new Error('outbox consume outcome must be an object');
  return {
    stream: requiredString(body, 'stream'),
    entries: requiredNumber(body, 'entries'),
    processed: requiredNumber(body, 'processed'),
    skippedDuplicates: requiredNumber(body, 'skippedDuplicates'),
    proof: requiredString(body, 'proof'),
  };
}
