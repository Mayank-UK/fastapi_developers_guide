/**
 * Domain models for the messaging topic's stream lab (demo block id
 * `msg:stream`) — the client-side shape of the /api/demo/msg/stream*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is interactive: the roster panel carries the log in id order
 * with its pending backlog, and four actions run for real — produce
 * (XADD), consume as the healthy or poison persona (XREADGROUP, XACK
 * only for the healthy one), the pending list (XPENDING), and reclaim
 * (XAUTOCLAIM to the healthy consumer).
 */

/** One entry in a stream: the broker's id plus the event it carries. */
export interface StreamEntry {
  id: string;
  eventId: string;
  eventType: string;
  payload: string;
}

/** One pending-entries-list row: delivered, owned, not yet acknowledged. */
export interface PendingEntry {
  entryId: string;
  consumer: string;
  idleMs: number;
  deliveries: number;
}

/** Which consumer persona a read round plays. */
export type ConsumeMode = 'healthy' | 'poison';

/** Wire shape of GET /api/demo/msg/stream — the roster panel's facts. */
export interface StreamPanel {
  namespace: string;
  stream: string;
  group: string;
  healthyConsumer: string;
  poisonConsumer: string;
  length: number;
  displayed: number;
  lastId: string | null;
  entries: StreamEntry[];
  pendingCount: number;
  produceEndpoint: string;
  consumeEndpoint: string;
  pendingEndpoint: string;
  reclaimEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/msg/stream/produce. */
export interface ProduceOutcome {
  stream: string;
  eventId: string;
  entryId: string;
  note: string;
  length: number;
  detail: string;
}

/** Wire shape of POST /api/demo/msg/stream/consume. */
export interface ConsumeOutcome {
  stream: string;
  group: string;
  consumer: string;
  mode: ConsumeMode;
  delivered: StreamEntry[];
  acked: number;
  detail: string;
}

/** Wire shape of GET /api/demo/msg/stream/pending. */
export interface PendingListOutcome {
  stream: string;
  group: string;
  entries: PendingEntry[];
  detail: string;
}

/** Wire shape of POST /api/demo/msg/stream/reclaim. */
export interface ReclaimOutcome {
  stream: string;
  group: string;
  consumer: string;
  minIdleMs: number;
  claimed: StreamEntry[];
  acked: number;
  detail: string;
}
