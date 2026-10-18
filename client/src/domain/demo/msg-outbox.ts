/**
 * Domain models for the messaging topic's outbox lab (demo block id
 * `msg:outbox`) — the client-side shape of the /api/demo/msg/outbox*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is interactive: the roster panel carries the outbox table's
 * counts, recent rows, the relay's stream, and telemetry; the actions
 * are the one-transaction create (post + event, both or neither), the
 * relay cycle (with the optional crash window), and the idempotent
 * consume whose counts prove the exactly-once effect.
 */

import type { StreamEntry } from './msg-stream';

/** One outbox row: the event, its aggregate, its publication state. */
export interface OutboxRow {
  eventId: string;
  eventType: string;
  aggregate: string;
  payload: string;
  createdAt: string;
  publishedAt: string | null;
}

/** The outbox table's three counts — the relay's world in one row. */
export interface OutboxStats {
  total: number;
  published: number;
  unpublished: number;
}

/** The outbox demo's in-process counters. */
export interface OutboxTelemetry {
  creates: number;
  relayCycles: number;
  crashSimulations: number;
  publishes: number;
  eventsProcessed: number;
  duplicatesSkipped: number;
}

/** Wire shape of GET /api/demo/msg/outbox — the roster panel's facts. */
export interface OutboxPanel {
  namespace: string;
  stream: string;
  table: string;
  stats: OutboxStats;
  outbox: OutboxRow[];
  streamEntries: StreamEntry[];
  telemetry: OutboxTelemetry;
  postsEndpoint: string;
  relayEndpoint: string;
  consumeEndpoint: string;
  reasoning: string;
}

/** The committed post half of the dual write. */
export interface OutboxPostRow {
  id: number;
  slug: string;
  title: string;
  author: string;
  createdAt: string;
}

/** Wire shape of POST /api/demo/msg/outbox/posts — both halves, or neither. */
export interface OutboxWriteOutcome {
  committed: boolean;
  post: OutboxPostRow | null;
  event: OutboxRow | null;
  failure: string | null;
  detail: string;
}

/** One publish inside a relay cycle: which event landed on which id. */
export interface PublishedEntry {
  eventId: string;
  entryId: string;
  aggregate: string;
}

/** Wire shape of POST /api/demo/msg/outbox/relay — poll, publish, mark (or die). */
export interface RelayOutcome {
  cycle: number;
  stream: string;
  discovered: number;
  published: PublishedEntry[];
  marked: number;
  crashed: boolean;
  detail: string;
}

/** Wire shape of POST /api/demo/msg/outbox/consume — the dedupe proof. */
export interface OutboxConsumeOutcome {
  stream: string;
  entries: number;
  processed: number;
  skippedDuplicates: number;
  proof: string;
}
