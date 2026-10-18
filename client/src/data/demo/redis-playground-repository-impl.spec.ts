import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { RedisPlaygroundApi } from './redis-playground-api';
import { RedisPlaygroundRepositoryImpl } from './redis-playground-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * RedisPlaygroundRepositoryImpl spec — fixture-driven: the playground
 * payload (structures, TTL proof, pub/sub proof) round-trips, malformed
 * payloads resolve as Failed Results, never throw.
 */

const REDIS_PLAYGROUND_URL = '/api/demo/redis/playground?tag=demo';

const payload = {
  namespace: 'guide_demo:redis:*',
  tag: 'demo',
  structures: [
    {
      kind: 'string',
      key: 'guide_demo:redis:demo:hits',
      description: 'The atomic counter.',
      commands: ['SET guide_demo:redis:demo:hits "1"'],
      outcome: 'each INCR returned the new value (2, then 3)',
      values: [
        { label: 'GET right after SET', value: '1' },
        { label: 'GET after INCR x2', value: '3' },
      ],
    },
    {
      kind: 'zset',
      key: 'guide_demo:redis:demo:leaderboard',
      description: 'Members with scores, kept ordered.',
      commands: ['ZADD …', 'ZRANGE … WITHSCORES'],
      outcome: 'zadd added 3 member(s)',
      values: [{ label: 'grace', value: 'score 100 · rank 1' }],
    },
  ],
  ttl: {
    key: 'guide_demo:redis:demo:flash',
    ttlSeconds: 2,
    commands: ['SET … EX 2', 'TTL …'],
    ttlFirstRead: 2,
    absentAfterExpiry: true,
    waitedMs: 2257,
    proof: 'the store evicted it on its own clock.',
  },
  pubsub: {
    channel: 'guide_demo:redis:demo:events',
    payload: '{"tag": "demo", "event": "playground", "n": 1}',
    commands: ['SUBSCRIBE …', 'PUBLISH …'],
    receivers: 1,
    receivedPayload: '{"tag": "demo", "event": "playground", "n": 1}',
    matched: true,
    proof: 'both sides of the wire, one message.',
  },
  reasoning: 'Every row above is what the live store answered.',
};

function makeRepository(): RedisPlaygroundRepositoryImpl {
  return new RedisPlaygroundRepositoryImpl(new RedisPlaygroundApi(createAppConfig()));
}

describe('RedisPlaygroundRepositoryImpl', () => {
  it('fetches and parses the playground with both proofs', async () => {
    stubApiFetch([{ url: REDIS_PLAYGROUND_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().playground('demo');

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.namespace).toBe('guide_demo:redis:*');
      expect(result.value.structures).toHaveLength(2);
      expect(result.value.structures[0]?.kind).toBe('string');
      expect(result.value.structures[0]?.values[1]).toEqual({
        label: 'GET after INCR x2',
        value: '3',
      });
      expect(result.value.ttl.absentAfterExpiry).toBe(true);
      expect(result.value.pubsub.matched).toBe(true);
      expect(result.value.pubsub.receivedPayload).toBe(result.value.pubsub.payload);
    }
  });

  it('rejects a payload whose structure kind is unknown', async () => {
    const poisoned = {
      ...payload,
      structures: [{ ...payload.structures[0], kind: 'bloom' }],
    };
    stubApiFetch([{ url: REDIS_PLAYGROUND_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().playground('demo');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().playground('demo');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
