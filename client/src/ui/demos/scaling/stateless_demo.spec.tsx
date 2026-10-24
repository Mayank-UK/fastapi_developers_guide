import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ScalingStatelessDemo from './stateless_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetScalingStatelessDemoUseCase } from '../../../domain/demo/get-scaling-stateless-demo-usecase';
import type { StatelessPanel } from '../../../domain/demo/scaling-stateless';

/**
 * ScalingStatelessDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the process facts, the nine-step two-replica round (the
 * process-local patch that never crosses, the shared counter that
 * does), the three verdicts, the state-placement inventory with its
 * placement tones, and the honesty note; a failed read degrades to the
 * shared error panel with recovery.
 */

const fakePanel: StatelessPanel = {
  process: [
    {
      id: 'processes',
      label: 'processes serving this app right now',
      value: '1 — the dev stack runs uvicorn --reload as a single process',
    },
    { id: 'pid', label: "this process's pid", value: '4312 — every in-process store below lives in this one heap' },
    {
      id: 'scenario-now',
      label: 'the live scenario flags this process holds',
      value: 'dataMode=fake · injectFailure=none — read from app.state.scenario, not assumed',
    },
    {
      id: 'posts-now',
      label: "posts in this process's in-memory store",
      value: '12 posts in this process right now (12 of them the deterministic seed)',
    },
  ],
  replicaRound: [
    { step: 1, side: 'process', label: 'the serving process', detail: 'one process', observed: 'the round below constructs exactly that world, twice' },
    { step: 2, side: 'replica-a', label: "replica A's world is built", detail: 'a fresh ScenarioStore', observed: 'dataMode=fake · injectFailure=none' },
    { step: 3, side: 'replica-a', label: 'replica A serves a PATCH: injectFailure → latency', detail: 'the write lands in replica A heap', observed: 'dataMode=fake · injectFailure=latency' },
    { step: 4, side: 'replica-b', label: "replica B's world is built the same way", detail: 'a second ScenarioStore', observed: 'dataMode=fake · injectFailure=none' },
    { step: 5, side: 'replica-b', label: 'replica B answers the same request', detail: 'process-local state does not follow the request', observed: 'dataMode=fake · injectFailure=none — A patch is invisible' },
    { step: 6, side: 'shared', label: 'the same round against the shared counter', detail: 'redis INCR on guide_demo:scaling:shared', observed: 'key deleted — a fresh stage' },
    { step: 7, side: 'replica-a', label: 'replica A increments the shared key', detail: 'INCR is atomic', observed: 'INCR → 1' },
    { step: 8, side: 'replica-b', label: 'replica B increments the same key', detail: 'B answer includes A write', observed: 'INCR → 2 — externalized state follows the request' },
    { step: 9, side: 'shared', label: 'the key outlives the request', detail: 'EXPIRE 60s', observed: 'value 2 with a 60s self-cleaning ttl' },
  ],
  verdicts: [
    { id: 'in-process', label: 'the in-process half (steps 2–5)', value: "replica A's patch was invisible to replica B" },
    { id: 'externalized', label: 'the externalized half (steps 6–9)', value: "replica B's INCR returned 2 — both writes accumulated on one value the store owns" },
    { id: 'the-trade', label: 'the trade this repo makes on purpose', value: 'the guide keeps posts, auth state, scenario flags, and rate budgets in-process' },
  ],
  inventory: [
    { id: 'posts-substrate', state: 'the posts substrate: 12 seeded posts', holder: 'InMemoryPostRepository', placement: 'in-process', where: 'app.state.posts_repository', restart: 'the seed is re-derived on boot', evidence: '12 posts in this process right now' },
    { id: 'postgres', state: 'authors, posts, comments, audit_log, outbox', holder: 'the postgres container', placement: 'externalized', where: 'reached through the app ONE async engine', restart: 'nothing is lost', evidence: 'the schema is owned by Alembic migrations 0001→0004' },
    { id: 'jwt', state: 'claims signed with HS256', holder: 'the client', placement: 'client-side', where: 'the token itself', restart: 'verifies as long as the signing secret is stable', evidence: 'the claims ARE the state' },
  ],
  honestyNote:
    'Every row on this panel is real: the process facts were read off this very app composition root, and the shared counter is a real redis INCR against the live store.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<StatelessPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetScalingStatelessDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetScalingStatelessDemoUseCase);
}

describe('ScalingStatelessDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['scaling:stateless']).toBeDefined();
  });

  it('renders the process facts, the round with both halves, the verdicts, and the inventory', async () => {
    stubUseCase(() => success(fakePanel));

    render(<ScalingStatelessDemo />);

    await waitFor(() => expect(screen.getByTestId('scl-panel')).toBeInTheDocument());

    expect(screen.getByTestId('scl-f-processes')).toHaveTextContent('uvicorn --reload');
    expect(screen.getByTestId('scl-f-scenario-now')).toHaveTextContent('dataMode=fake');

    const patch = screen.getByTestId('scl-r-3');
    expect(patch).toHaveTextContent('[replica-a]');
    expect(patch).toHaveTextContent('injectFailure=latency');
    const blind = screen.getByTestId('scl-r-5');
    expect(blind).toHaveTextContent('[replica-b]');
    expect(blind).toHaveTextContent('A patch is invisible');
    const shared = screen.getByTestId('scl-r-8');
    expect(shared).toHaveTextContent('[replica-b]');
    expect(shared).toHaveTextContent('INCR → 2');
    expect(screen.getByTestId('scl-r-9')).toHaveTextContent('60s self-cleaning ttl');

    expect(screen.getByTestId('scl-f-in-process')).toHaveTextContent('invisible to replica B');
    expect(screen.getByTestId('scl-f-externalized')).toHaveTextContent('returned 2');
    expect(screen.getByTestId('scl-f-the-trade')).toHaveTextContent('in-process');

    expect(screen.getByTestId('scl-i-posts-substrate')).toHaveTextContent('in-process');
    expect(screen.getByTestId('scl-i-posts-substrate')).toHaveTextContent(
      'the seed is re-derived on boot',
    );
    expect(screen.getByTestId('scl-i-postgres')).toHaveTextContent('externalized');
    expect(screen.getByTestId('scl-i-jwt')).toHaveTextContent('client-side');

    expect(screen.getByTestId('scl-honesty-note')).toHaveTextContent('real redis INCR');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The statelessness panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-scaling-1',
            }),
          )
        : success(fakePanel);
    });

    render(<ScalingStatelessDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('scl-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
