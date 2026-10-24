import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ThirdPartyHubDemo from './hub_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetThirdPartyHubDemoUseCase } from '../../../domain/demo/get-thirdparty-hub-demo-usecase';
import type { ThirdPartyHubPanel } from '../../../domain/demo/thirdparty-hub';

/**
 * ThirdPartyHubDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * panel renders the verified decision walk, the integration inventory
 * with its failure modes, the value-free secrets rows, the quotas with
 * their live/constant sources, and the honesty note; a failed read
 * degrades to the shared error panel with recovery.
 */

const fakePanel: ThirdPartyHubPanel = {
  decisions: [
    {
      id: 'graphql-engine',
      choice: 'integrate',
      subject: 'the GraphQL API surface (POST /api/graphql)',
      package: 'strawberry-graphql[fastapi]',
      reason: 'a GraphQL engine is a parser, a type system, an executor, and a loader',
      blastRadius: 'every GraphQL query the playground console posts',
      verified:
        "server/pyproject.toml carries 'strawberry-graphql[fastapi]>=0.335.0' (parsed on this request)",
    },
    {
      id: 'circuit-breaker',
      choice: 'build',
      subject: 'the circuit breaker substrate',
      package: 'guide/domain/reliability/breaker.py',
      reason: 'the substrate is about a hundred readable lines with an injected clock',
      blastRadius: 'the reliability breaker demo',
      verified: 'guide/domain/reliability/breaker.py exists in this server tree (checked on this request)',
    },
  ],
  integrations: [
    {
      id: 'redis',
      kind: 'backing-service',
      name: 'Redis 8',
      detail: 'ONE lazy redis.asyncio client (two-second socket timeouts) shared by five adapters',
      whenDown: 'only the redis-backed demos answer the 503 envelope',
      evidence: 'the shared client + adapter wiring in server/guide/main.py',
    },
    {
      id: 'ghcr-images',
      kind: 'artifact',
      name: 'GHCR release images',
      detail: 'ghcr.io/mayank-uk/fastapi-guide-{server,client}:${IMAGE_TAG:?}',
      whenDown: 'a pull failure stops the release before any traffic flips',
      evidence: 'both image rails found in .docker/docker-compose.prod.yml (containment-checked on this request)',
    },
  ],
  secrets: [
    {
      id: 'jwt-secret',
      envVar: 'FDG_JWT_SECRET',
      scope: 'signs every HS256 access token',
      blastRadius: 'a leak mints tokens for ANY user until the key rotates',
      handling: "AppConfig refuses the dev default outside dev (fail-fast validator at boot)",
      evidence: 'config field jwt_secret (server/guide/core/config.py)',
    },
    {
      id: 'db-password',
      envVar: 'FDG_DB_PASSWORD (inside FDG_DATABASE_URL)',
      scope: 'the PostgreSQL credential — user postgres, database guide',
      blastRadius: 'a leak is full read/write to the guide database',
      handling: 'required rail in the prod compose; the real value lives only in the GitHub production environment',
      evidence: 'all three required rails found in .docker/docker-compose.prod.yml (containment-checked on this request)',
    },
  ],
  quotas: [
    {
      id: 'rate-limit',
      quota: '5 hits / 10s per client ip + route',
      scope: 'every route the limiter guards',
      atCeiling: 'the 429 envelope with Retry-After (rounded up, never zero)',
      source: 'live',
    },
    {
      id: 'room-ceiling',
      quota: '8 members per room',
      scope: 'the realtime chat rooms',
      atCeiling: 'join refused under the lock with close code 1013 (try again later)',
      source: 'constant',
    },
  ],
  honestyNote:
    'Every row was derived on this request. The secrets inventory carries NAMES and blast radii, never values — the builder never reads a secret, so the wire cannot carry one.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<ThirdPartyHubPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetThirdPartyHubDemoUseCase, {
    hub: () => Promise.resolve(respond()),
  } as unknown as GetThirdPartyHubDemoUseCase);
}

describe('ThirdPartyHubDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['thirdparty:hub']).toBeDefined();
  });

  it('renders the verified decisions, the inventory, the value-free secrets, and the quotas', async () => {
    stubUseCase(() => success(fakePanel));

    render(<ThirdPartyHubDemo />);

    await waitFor(() => expect(screen.getByTestId('tp-panel')).toBeInTheDocument());

    const bought = screen.getByTestId('tp-d-graphql-engine');
    expect(bought).toHaveTextContent('[integrate]');
    expect(bought).toHaveTextContent("carries 'strawberry-graphql[fastapi]>=0.335.0'");
    const built = screen.getByTestId('tp-d-circuit-breaker');
    expect(built).toHaveTextContent('[build]');
    expect(built).toHaveTextContent('exists in this server tree');

    expect(screen.getByTestId('tp-i-redis')).toHaveTextContent('backing-service');
    expect(screen.getByTestId('tp-i-redis')).toHaveTextContent('503 envelope');
    expect(screen.getByTestId('tp-i-ghcr-images')).toHaveTextContent('artifact');
    expect(screen.getByTestId('tp-i-ghcr-images')).toHaveTextContent('containment-checked');

    const jwt = screen.getByTestId('tp-s-jwt-secret');
    expect(jwt).toHaveTextContent('FDG_JWT_SECRET');
    expect(jwt).toHaveTextContent('mints tokens for ANY user');
    expect(screen.getByTestId('tp-s-db-password')).toHaveTextContent('full read/write');

    expect(screen.getByTestId('tp-q-rate-limit')).toHaveTextContent('5 hits / 10s');
    expect(screen.getByTestId('tp-q-rate-limit')).toHaveTextContent('(live)');
    expect(screen.getByTestId('tp-q-room-ceiling')).toHaveTextContent('8 members per room');
    expect(screen.getByTestId('tp-q-room-ceiling')).toHaveTextContent('(constant)');

    expect(screen.getByTestId('tp-honesty-note')).toHaveTextContent('never values');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The third-party hub did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-thirdparty-1',
            }),
          )
        : success(fakePanel);
    });

    render(<ThirdPartyHubDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('tp-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
