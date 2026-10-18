/**
 * Domain models for the redis topic's playground (demo block id
 * `redis:playground`) — the client-side shape of
 * GET /api/demo/redis/playground. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * One payload carries the whole scripted walk: the five core structures
 * with their real read-backs (string with the atomic INCR counter, hash,
 * list, set, sorted set), the honest TTL expiry proof (the live clock,
 * then the key's absence after the bounded wait), and a real pub/sub
 * round-trip reported from both sides of the wire.
 */

/** One value a structure read returned, as a display string. */
export interface StructureValueRow {
  label: string;
  value: string;
}

/** One Redis structure walked with real commands and real results. */
export interface StructureRow {
  kind: 'string' | 'hash' | 'list' | 'set' | 'zset';
  key: string;
  description: string;
  commands: string[];
  outcome: string;
  values: StructureValueRow[];
}

/** The TTL exhibit: set with an inline EX, the clock, the absence proof. */
export interface TtlProofRow {
  key: string;
  ttlSeconds: number;
  commands: string[];
  ttlFirstRead: number;
  absentAfterExpiry: boolean;
  waitedMs: number;
  proof: string;
}

/** The pub/sub exhibit: one real message, both sides of the wire. */
export interface PubsubProofRow {
  channel: string;
  payload: string;
  commands: string[];
  receivers: number;
  receivedPayload: string;
  matched: boolean;
  proof: string;
}

/** The whole playground payload: structures, TTL proof, pub/sub proof. */
export interface RedisPlaygroundDemo {
  namespace: string;
  tag: string;
  structures: StructureRow[];
  ttl: TtlProofRow;
  pubsub: PubsubProofRow;
  reasoning: string;
}
