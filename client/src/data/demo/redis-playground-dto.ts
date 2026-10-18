import {
  type PubsubProofRow,
  type RedisPlaygroundDemo,
  type StructureRow,
  type StructureValueRow,
  type TtlProofRow,
} from '../../domain/demo/redis-playground';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * RedisPlaygroundDTO — the wire/transport shapes of the redis playground:
 * the five structure rows, the TTL proof, and the pub/sub proof.
 */

export type RedisPlaygroundDto = RedisPlaygroundDemo;

const STRUCTURE_KINDS = ['string', 'hash', 'list', 'set', 'zset'] as const;

function structureValueFromJson(value: unknown): StructureValueRow {
  if (!isRecord(value)) throw new Error('structure value row must be an object');
  return {
    label: requiredString(value, 'label'),
    value: requiredString(value, 'value'),
  };
}

function structureFromJson(value: unknown): StructureRow {
  if (!isRecord(value)) throw new Error('structure row must be an object');
  const kind = requiredString(value, 'kind');
  if (!STRUCTURE_KINDS.includes(kind as (typeof STRUCTURE_KINDS)[number])) {
    throw new Error(`unknown structure kind: ${kind}`);
  }
  return {
    kind: kind as StructureRow['kind'],
    key: requiredString(value, 'key'),
    description: requiredString(value, 'description'),
    commands: requiredArray(value, 'commands').map((command) => {
      if (typeof command !== 'string') throw new Error('expected command string');
      return command;
    }),
    outcome: requiredString(value, 'outcome'),
    values: requiredArray(value, 'values').map(structureValueFromJson),
  };
}

function ttlFromJson(body: Record<string, unknown>): TtlProofRow {
  const ttl = requiredRecord(body, 'ttl');
  return {
    key: requiredString(ttl, 'key'),
    ttlSeconds: requiredNumber(ttl, 'ttlSeconds'),
    commands: requiredArray(ttl, 'commands').map((command) => {
      if (typeof command !== 'string') throw new Error('expected command string');
      return command;
    }),
    ttlFirstRead: requiredNumber(ttl, 'ttlFirstRead'),
    absentAfterExpiry: requiredBoolean(ttl, 'absentAfterExpiry'),
    waitedMs: requiredNumber(ttl, 'waitedMs'),
    proof: requiredString(ttl, 'proof'),
  };
}

function pubsubFromJson(body: Record<string, unknown>): PubsubProofRow {
  const pubsub = requiredRecord(body, 'pubsub');
  return {
    channel: requiredString(pubsub, 'channel'),
    payload: requiredString(pubsub, 'payload'),
    commands: requiredArray(pubsub, 'commands').map((command) => {
      if (typeof command !== 'string') throw new Error('expected command string');
      return command;
    }),
    receivers: requiredNumber(pubsub, 'receivers'),
    receivedPayload: requiredString(pubsub, 'receivedPayload'),
    matched: requiredBoolean(pubsub, 'matched'),
    proof: requiredString(pubsub, 'proof'),
  };
}

/** Deserialize + validate the redis playground payload. */
export function redisPlaygroundFromJson(body: unknown): RedisPlaygroundDto {
  if (!isRecord(body)) throw new Error('redis playground demo must be an object');
  return {
    namespace: requiredString(body, 'namespace'),
    tag: requiredString(body, 'tag'),
    structures: requiredArray(body, 'structures').map(structureFromJson),
    ttl: ttlFromJson(body),
    pubsub: pubsubFromJson(body),
    reasoning: requiredString(body, 'reasoning'),
  };
}
