import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ExplorerDemo } from './explorer_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetErrorsExplorerDemoUseCase } from '../../../domain/demo/get-errors-explorer-demo-usecase';
import type {
  ErrorsPanel,
  InjectedRound,
  ObservedFailure,
  ProbeRound,
  ScenarioSnapshot,
} from '../../../domain/demo/errors-explorer';

/**
 * ExplorerDemo spec — fixture-driven (happy + failure): the panel renders
 * the eight kinds with the two recipe rows marked honestly; firing a live
 * kind shows the observed envelope beside the x-request-id header with the
 * match badge; the internal round shows the 500 AND the recovered probe;
 * the scenario sub-panel renders the snapshot and a probe round; a failed
 * panel degrades to the shared error panel with recovery.
 */

const observed: ObservedFailure = {
  kind: 'not_found',
  httpStatus: 404,
  code: 'not_found',
  message: "Post 'no-such-post' not found",
  requestId: 'body-id-1234567890',
  requestIdHeader: 'body-id-1234567890',
  headerMatchesBody: true,
  retryAfterSeconds: null,
  detailLine: null,
  attempts: null,
};

const injected: InjectedRound = {
  failure: {
    kind: 'internal',
    httpStatus: 500,
    code: 'internal',
    message: 'Internal server error.',
    requestId: 'five-aaaaaaaaaa',
    requestIdHeader: 'five-aaaaaaaaaa',
    headerMatchesBody: true,
    retryAfterSeconds: null,
    detailLine: null,
    attempts: null,
  },
  recovered: {
    status: 'healthy',
    injectFailure: 'none',
    detail: 'probe answered normally',
  },
};

const probeRound: ProbeRound = {
  outcome: { status: 'healthy', injectFailure: 'none', detail: 'probe answered normally' },
  failure: null,
};

const snapshot: ScenarioSnapshot = { dataMode: 'fake', injectFailure: 'none' };

const panel: ErrorsPanel = {
  kinds: [
    {
      kind: 'not_found',
      httpStatus: 404,
      defaultMessage: 'Resource not found.',
      raisedBy: 'use cases and thin routers',
      loggedAs: 'app_error · warning',
      trigger: {
        mode: 'live',
        method: 'GET',
        path: '/api/posts/no-such-post',
        body: null,
        prep: null,
        note: 'a well-formed id that names nothing',
      },
    },
    {
      kind: 'conflict',
      httpStatus: 409,
      defaultMessage: 'Resource conflict.',
      raisedBy: "the arq adapter's duplicate-refusal guard",
      loggedAs: 'app_error · warning',
      trigger: {
        mode: 'recipe',
        method: 'POST',
        path: '/api/demo/jobs/enqueue',
        body: null,
        prep: null,
        note: 'no live trigger BY DESIGN: the adapter never sends a duplicate id',
      },
    },
    {
      kind: 'internal',
      httpStatus: 500,
      defaultMessage: 'Internal server error.',
      raisedBy: 'the last-resort handler',
      loggedAs: 'unhandled_exception · error',
      trigger: {
        mode: 'live',
        method: 'GET',
        path: '/api/demo/errors/probe',
        body: null,
        prep: "PATCH /api/demo/scenario {\"injectFailure\": \"error\"} first",
        note: 'the scenario injection, honored by the probe',
      },
    },
  ],
  envelopeNote: 'every failure answers the same envelope with x-request-id.',
  scenario: {
    getEndpoint: '/api/demo/scenario',
    patchEndpoint: '/api/demo/scenario',
    modes: ['none', 'error', 'latency'],
    note: 'the runtime toggle every demo reads',
  },
  probe: {
    probeEndpoint: '/api/demo/errors/probe',
    latencySeconds: 1.5,
    healthyNote: 'answers 200 healthy',
    injectedNote: 'raises the genuine 500',
    latencyNote: 'sleeps out the injection',
  },
  reasoning: 'Eight kinds, one envelope.',
};

type Stubs = {
  panel?: () => Promise<Result<ErrorsPanel>>;
  fireNotFound?: () => Promise<Result<ObservedFailure>>;
  fireInternal?: () => Promise<Result<InjectedRound>>;
  scenario?: () => Promise<Result<ScenarioSnapshot>>;
  probe?: () => Promise<Result<ProbeRound>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetErrorsExplorerDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    fireValidationFailure: async () => success(observed),
    fireUnauthorizedFailure: async () => success(observed),
    fireForbiddenFailure: async () => success(observed),
    fireNotFoundFailure: stubs.fireNotFound ?? (async () => success(observed)),
    fireRateLimitedFailure: async () => success(observed),
    fireInternalFailure: stubs.fireInternal ?? (async () => success(injected)),
    readScenario: stubs.scenario ?? (async () => success(snapshot)),
    setInjectFailure: async () => success(snapshot),
    probe: stubs.probe ?? (async () => success(probeRound)),
  } as unknown as GetErrorsExplorerDemoUseCase);
}

describe('ExplorerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['errors:explorer']).toBeDefined();
  });

  it('renders the kind rows with the recipe rows marked honestly', async () => {
    stubUseCase({});
    render(<ExplorerDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('errors-explorer-kinds')).toBeInTheDocument(),
    );
    const kinds = screen.getByTestId('errors-explorer-kinds');
    expect(kinds).toHaveTextContent('not_found · 404');
    expect(kinds).toHaveTextContent('conflict · 409');
    expect(kinds).toHaveTextContent('recipe only: POST /api/demo/jobs/enqueue');
    expect(kinds).toHaveTextContent('no live trigger BY DESIGN');
  });

  it('fires a live kind and shows the envelope beside the matching header id', async () => {
    stubUseCase({});
    render(<ExplorerDemo />);
    const fire = await screen.findAllByRole('button', { name: 'fire the real trigger' });
    fire[0]?.click();
    await waitFor(() =>
      expect(screen.getByTestId('errors-explorer-result')).toBeInTheDocument(),
    );
    const result = screen.getByTestId('errors-explorer-result');
    expect(result).toHaveTextContent('404 · not_found');
    expect(result).toHaveTextContent("Post 'no-such-post' not found");
    expect(result).toHaveTextContent('✓ match');
  });

  it('renders the injected round: the 500 and the recovered probe', async () => {
    stubUseCase({});
    render(<ExplorerDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('errors-explorer-scenario')).toBeInTheDocument(),
    );
    // The internal kind's button is the second live trigger in the fixture.
    const fire = await screen.findAllByRole('button', { name: 'fire the real trigger' });
    fire[1]?.click();
    await waitFor(() =>
      expect(screen.getByTestId('errors-explorer-injected')).toBeInTheDocument(),
    );
    const injectedCard = screen.getByTestId('errors-explorer-injected');
    expect(injectedCard).toHaveTextContent('500 · internal');
    expect(injectedCard).toHaveTextContent('Internal server error.');
    expect(injectedCard).toHaveTextContent('recovered');
  });

  it('renders the scenario snapshot and a healthy probe round', async () => {
    stubUseCase({});
    render(<ExplorerDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('errors-explorer-scenario')).toBeInTheDocument(),
    );
    const scenario = screen.getByTestId('errors-explorer-scenario');
    expect(scenario).toHaveTextContent('dataMode fake · injectFailure none');
    const probe = screen.getByRole('button', { name: 'probe' });
    probe.click();
    await waitFor(() =>
      expect(screen.getByTestId('errors-explorer-probe-result')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('errors-explorer-probe-result')).toHaveTextContent(
      '200 · healthy · injectFailure none',
    );
  });

  it('degrades to the shared error panel when the panel call fails', async () => {
    stubUseCase({
      panel: async () =>
        failed(
          new ServerFailure('Could not reach the server.', {
            code: 'network_error',
            status: 0,
          }),
        ),
    });
    render(<ExplorerDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('Could not load the errors explorer');
  });
});
