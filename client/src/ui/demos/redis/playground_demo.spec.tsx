import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RedisPlaygroundDemo } from './playground_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetRedisPlaygroundDemoUseCase } from '../../../domain/demo/get-redis-playground-demo-usecase';
import type { RedisPlaygroundDemo as RedisPlaygroundModel } from '../../../domain/demo/redis-playground';

/**
 * RedisPlaygroundDemo spec — fixture-driven (happy + failure): all five
 * structures render with their real commands and read-backs, the TTL
 * proof shows the measured clock and the absence, the pub/sub proof
 * shows both sides of the wire, and failures degrade to the shared
 * error panel with recovery.
 */

const run: RedisPlaygroundModel = {
  namespace: 'guide_demo:redis:*',
  tag: 'demo',
  structures: [
    {
      kind: 'string',
      key: 'guide_demo:redis:demo:hits',
      description: 'A string key holding a number, INCR’d twice.',
      commands: ['SET guide_demo:redis:demo:hits "1"', 'INCR guide_demo:redis:demo:hits'],
      outcome: 'each INCR returned the new value (2, then 3)',
      values: [
        { label: 'GET right after SET', value: '1' },
        { label: 'GET after INCR x2', value: '3' },
      ],
    },
    {
      kind: 'hash',
      key: 'guide_demo:redis:demo:profile',
      description: 'A hash stores field-value pairs under one key.',
      commands: ['HSET guide_demo:redis:demo:profile …'],
      outcome: 'hset added 3 field(s); hgetall answered all 3 back',
      values: [{ label: 'name', value: 'the redis playground' }],
    },
    {
      kind: 'list',
      key: 'guide_demo:redis:demo:timeline',
      description: 'A list is a linked sequence.',
      commands: ['LPUSH guide_demo:redis:demo:timeline …', 'LRANGE guide_demo:redis:demo:timeline 0 -1'],
      outcome: 'lpush returned 3; the newest entry sits at index 0',
      values: [{ label: 'LRANGE 0 -1 [0]', value: 'first:demo' }],
    },
    {
      kind: 'set',
      key: 'guide_demo:redis:demo:tags',
      description: 'A set holds unique members.',
      commands: ['SADD guide_demo:redis:demo:tags …', 'SMEMBERS guide_demo:redis:demo:tags'],
      outcome: 'sadd added 4 member(s)',
      values: [{ label: 'member', value: 'cache' }],
    },
    {
      kind: 'zset',
      key: 'guide_demo:redis:demo:leaderboard',
      description: 'A sorted set maps members to scores.',
      commands: ['ZADD guide_demo:redis:demo:leaderboard …', 'ZRANGE guide_demo:redis:demo:leaderboard 0 -1 WITHSCORES'],
      outcome: 'zadd added 3 member(s)',
      values: [{ label: 'grace', value: 'score 100 · rank 1' }],
    },
  ],
  ttl: {
    key: 'guide_demo:redis:demo:flash',
    ttlSeconds: 2,
    commands: ['SET guide_demo:redis:demo:flash "…" EX 2', 'TTL guide_demo:redis:demo:flash'],
    ttlFirstRead: 2,
    absentAfterExpiry: true,
    waitedMs: 2257,
    proof: 'the key lived its configured 2 s — the store evicted it on its own clock.',
  },
  pubsub: {
    channel: 'guide_demo:redis:demo:events',
    payload: '{"tag": "demo", "event": "playground", "n": 1}',
    commands: ['SUBSCRIBE guide_demo:redis:demo:events', 'PUBLISH guide_demo:redis:demo:events …'],
    receivers: 1,
    receivedPayload: '{"tag": "demo", "event": "playground", "n": 1}',
    matched: true,
    proof: 'PUBLISH answered 1 and the bounded listener collected the identical payload.',
  },
  reasoning: 'Every row above is what the live store answered under guide_demo:redis:*.',
};

function stubUseCase(result: (tag: string) => Promise<Result<RedisPlaygroundModel>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetRedisPlaygroundDemoUseCase, {
    run: result,
  } as unknown as GetRedisPlaygroundDemoUseCase);
}

describe('RedisPlaygroundDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['redis:playground']).toBeDefined();
  });

  it('renders the five structures, the TTL proof, and the pub/sub round-trip', async () => {
    stubUseCase(async () => success(run));

    render(<RedisPlaygroundDemo />);

    await waitFor(() => expect(screen.getByTestId('redis-playground-ttl')).toBeInTheDocument());
    expect(screen.getByTestId('redis-playground-string')).toHaveTextContent(
      'each INCR returned the new value (2, then 3)',
    );
    expect(screen.getByTestId('redis-playground-string')).toHaveTextContent('GET after INCR x2 = 3');
    expect(screen.getByTestId('redis-playground-hash')).toHaveTextContent(
      'name = the redis playground',
    );
    expect(screen.getByTestId('redis-playground-list')).toHaveTextContent('first:demo');
    expect(screen.getByTestId('redis-playground-set')).toHaveTextContent('member = cache');
    expect(screen.getByTestId('redis-playground-zset')).toHaveTextContent('score 100 · rank 1');
    expect(screen.getByTestId('redis-playground-ttl-proof')).toHaveTextContent(
      'clock read 2s · waited 2257ms · absent after expiry: true',
    );
    expect(screen.getByTestId('redis-playground-pubsub-proof')).toHaveTextContent(
      'publish answered 1 receiver(s) · listener matched: true',
    );
    expect(screen.getByTestId('redis-playground-pubsub')).toHaveTextContent(
      'received: {"tag": "demo", "event": "playground", "n": 1}',
    );
    expect(screen.getByTestId('redis-playground-reasoning')).toHaveTextContent(
      'guide_demo:redis:*',
    );
  });

  it('re-runs with the picked tag from the picker', async () => {
    const tags: string[] = [];
    stubUseCase(async (tag) => {
      tags.push(tag);
      return success(run);
    });

    render(<RedisPlaygroundDemo />);
    await waitFor(() => expect(screen.getByTestId('redis-playground-ttl')).toBeInTheDocument());
    screen.getByRole('button', { name: 'tour' }).click();
    await waitFor(() => expect(tags).toEqual(['demo', 'tour']));
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('Redis is unreachable.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-65',
            }),
          )
        : success(run);
    });

    render(<RedisPlaygroundDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('redis-playground-ttl')).toBeInTheDocument());
  });
});
