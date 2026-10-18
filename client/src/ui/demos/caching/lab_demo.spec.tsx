import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { CachingLabDemo } from './lab_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetCachingLabDemoUseCase } from '../../../domain/demo/get-caching-lab-demo-usecase';
import type {
  CachingLabDemo as CachingLabModel,
  ConditionalRound,
} from '../../../domain/demo/caching-lab';

/**
 * CachingLabDemo spec — fixture-driven (happy + failure): the state
 * panel renders the key, liveness, and counters with the simulated-cost
 * label; the fetch button shows the real round (status, x-cache, etag);
 * the conditional console shows both rounds and the 304 proof; the
 * invalidate and stampede buttons render their outcomes; failures
 * degrade to the shared error panel with recovery.
 */

const roster: CachingLabModel = {
  namespace: 'guide_demo:caching:*',
  key: 'guide_demo:caching:posts:v1',
  ttlSeconds: 2,
  originCostMs: 120,
  originCostNote: 'simulated — the real substrate answers in microseconds',
  postsEndpoint: '/api/demo/caching/posts',
  invalidateEndpoint: '/api/demo/caching/invalidate',
  stampedeEndpoint: '/api/demo/caching/stampede',
  state: {
    key: 'guide_demo:caching:posts:v1',
    present: false,
    ttlSeconds: 2,
    ttlRemainingS: null,
    sizeBytes: null,
    etag: null,
    lastOutcome: null,
    telemetry: { hits: 0, misses: 0, coalesced: 0, invalidations: 0 },
  },
  reasoning: 'One key caches the newest-posts page as its canonical JSON string.',
};

const freshRound: ConditionalRound = {
  status: 200,
  etag: '"abc0123456789def"',
  cacheControl: 'no-cache',
  cache: 'miss',
  elapsedMs: 124,
  ageMs: null,
  originFetches: 1,
  hits: 0,
  bodyBytes: 512,
};

const revalidatedRound: ConditionalRound = {
  ...freshRound,
  status: 304,
  cache: 'hit',
  elapsedMs: 2,
  ageMs: 1000,
  hits: 1,
  bodyBytes: 0,
};

type Stubs = {
  lab?: () => Promise<Result<CachingLabModel>>;
  conditionalRound?: (ifNoneMatch?: string) => Promise<Result<ConditionalRound>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetCachingLabDemoUseCase, {
    lab: stubs.lab ?? (async () => success(roster)),
    conditionalRound:
      stubs.conditionalRound ??
      (async (ifNoneMatch?: string) =>
        success(ifNoneMatch === undefined ? freshRound : revalidatedRound)),
    invalidate: async () =>
      success({
        key: roster.key,
        deletedEntries: 1,
        telemetry: roster.state.telemetry,
        detail: 'deleted 1 entry — the next read is a miss and refills from the origin',
      }),
    stampede: async () =>
      success({
        requests: 8,
        originFetches: 1,
        servedWarm: 7,
        wallMs: 131,
        rounds: [
          { index: 0, outcome: 'miss', elapsedMs: 128 },
          { index: 1, outcome: 'coalesced', elapsedMs: 129 },
        ],
        proof: 'the per-key lock let one request fill while 7 waited',
      }),
  } as unknown as GetCachingLabDemoUseCase);
}

describe('CachingLabDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['caching:lab']).toBeDefined();
  });

  it('renders the state panel with the key, counters, and simulated-cost label', async () => {
    stubUseCase({});
    render(<CachingLabDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('caching-lab-state')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('caching-lab-liveness')).toHaveTextContent('no entry (ttl cap 2s)');
    expect(screen.getByTestId('caching-lab-telemetry')).toHaveTextContent(
      'hits 0 · misses 0 · coalesced 0 · invalidations 0',
    );
    expect(screen.getByTestId('caching-lab-state')).toHaveTextContent('simulated');
    expect(screen.getByTestId('caching-lab-reasoning')).toHaveTextContent(
      'canonical JSON string',
    );
  });

  it('shows the fetch round and the conditional console 304 proof', async () => {
    stubUseCase({});
    render(<CachingLabDemo />);
    await waitFor(() => expect(screen.getByTestId('caching-lab-state')).toBeInTheDocument());

    screen.getByRole('button', { name: 'GET /api/demo/caching/posts' }).click();
    await waitFor(() => expect(screen.getByTestId('caching-lab-round')).toBeInTheDocument());
    expect(screen.getByTestId('caching-lab-round')).toHaveTextContent(
      'round 1 · fresh GET: 200 · x-cache miss · 124ms',
    );

    screen.getByRole('button', { name: 'conditional round → 304' }).click();
    await waitFor(() => expect(screen.getByTestId('caching-lab-304-proof')).toBeInTheDocument());
    expect(screen.getByTestId('caching-lab-304-proof')).toHaveTextContent(
      '304 · validators matched · 0 body bytes',
    );
    expect(screen.getByTestId('caching-lab-round')).toHaveTextContent(
      'round 2 · If-None-Match sent back: 304 · x-cache hit',
    );
  });

  it('renders the invalidate and stampede outcomes with refreshed counters', async () => {
    stubUseCase({});
    render(<CachingLabDemo />);
    await waitFor(() => expect(screen.getByTestId('caching-lab-state')).toBeInTheDocument());

    screen.getByRole('button', { name: 'invalidate' }).click();
    await waitFor(() => expect(screen.getByTestId('caching-lab-invalidate')).toBeInTheDocument());
    expect(screen.getByTestId('caching-lab-invalidate')).toHaveTextContent('deleted 1 entry');

    screen.getByRole('button', { name: 'stampede ×8' }).click();
    await waitFor(() => expect(screen.getByTestId('caching-lab-stampede')).toBeInTheDocument());
    expect(screen.getByTestId('caching-lab-stampede-counts')).toHaveTextContent(
      '8 requests → origin fetches 1 · served warm 7',
    );
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      lab: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Redis is unreachable.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-c9',
              }),
            )
          : success(roster);
      },
    });

    render(<CachingLabDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('caching-lab-state')).toBeInTheDocument());
  });
});
