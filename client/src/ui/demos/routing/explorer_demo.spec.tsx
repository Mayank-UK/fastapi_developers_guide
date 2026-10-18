import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RoutingExplorerDemo } from './explorer_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetRoutingExplorerDemoUseCase } from '../../../domain/demo/get-routing-explorer-demo-usecase';
import type {
  RoutingExplorerData,
  RoutingExplorerRequest,
} from '../../../domain/demo/routing-explorer';

/**
 * RoutingExplorerDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the form fires
 * the simulated request line as configured, the matched verdict renders
 * with its bound parameters, the 405 verdict renders its allowed methods,
 * a non-absolute path is refused client-side, and failures degrade to the
 * shared error panel with recovery.
 */

const matchedFixture: RoutingExplorerData = {
  request: { method: 'GET', path: '/api/content/routing?deep=1' },
  routeCount: 15,
  outcome: 'matched',
  reasoning:
    "GET /api/content/routing matched the declared template /api/content/{topic_id}; " +
    "the router binds topic_id='routing'.",
  matchedPath: '/api/content/{topic_id}',
  matchedMethods: ['GET'],
  matchedTags: ['content'],
  pathParams: [{ name: 'topic_id', value: 'routing', source: 'path' }],
  queryParams: [{ name: 'deep', value: '1', source: 'query' }],
};

const head405Fixture: RoutingExplorerData = {
  request: { method: 'HEAD', path: '/api/health' },
  routeCount: 15,
  outcome: 'method_not_allowed',
  reasoning: 'There is no implicit HEAD in FastAPI.',
  matchedPath: '/api/health',
  matchedMethods: ['GET'],
  pathParams: [],
  queryParams: [],
  allowedMethods: ['GET'],
};

/** Capture the request the component fired, answering with a fixture. */
function stubUseCase(
  respond: (request: RoutingExplorerRequest) => Result<RoutingExplorerData>,
): RoutingExplorerRequest[] {
  const fired: RoutingExplorerRequest[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetRoutingExplorerDemoUseCase, {
    execute: (request: RoutingExplorerRequest) => {
      fired.push(request);
      return Promise.resolve(respond(request));
    },
  } as unknown as GetRoutingExplorerDemoUseCase);
  return fired;
}

describe('RoutingExplorerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['routing:explorer']).toBeDefined();
  });

  it('starts idle and matches the default path with bound parameters', async () => {
    const fired = stubUseCase(() => success(matchedFixture));

    render(<RoutingExplorerDemo />);

    expect(screen.getByTestId('rx-idle')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('rx-path'), {
      target: { value: '/api/content/routing?deep=1' },
    });
    fireEvent.click(screen.getByTestId('rx-match'));

    await waitFor(() => expect(screen.getByTestId('rx-result')).toBeInTheDocument());
    expect(fired).toEqual([{ method: 'GET', path: '/api/content/routing?deep=1' }]);

    expect(screen.getByTestId('rx-outcome')).toHaveTextContent('matched');
    expect(screen.getByTestId('rx-matched')).toHaveTextContent('/api/content/{topic_id}');
    expect(screen.getByTestId('rx-params')).toHaveTextContent('topic_id');
    expect(screen.getByTestId('rx-params')).toHaveTextContent("routing");
    expect(screen.getByTestId('rx-params')).toHaveTextContent('query');
    expect(screen.getByTestId('rx-reasoning')).toHaveTextContent('matched the declared template');
  });

  it('switches to HEAD and renders the 405 verdict with allowed methods', async () => {
    const fired = stubUseCase(() => success(head405Fixture));

    render(<RoutingExplorerDemo />);

    fireEvent.click(screen.getByTestId('rx-method-head'));
    fireEvent.change(screen.getByTestId('rx-path'), { target: { value: '/api/health' } });
    fireEvent.click(screen.getByTestId('rx-match'));

    await waitFor(() => expect(screen.getByTestId('rx-result')).toBeInTheDocument());
    expect(fired).toEqual([{ method: 'HEAD', path: '/api/health' }]);
    expect(screen.getByTestId('rx-outcome')).toHaveTextContent('method not allowed');
    expect(screen.getByTestId('rx-allowed')).toHaveTextContent('GET');
    expect(screen.getByTestId('rx-reasoning')).toHaveTextContent('no implicit HEAD');
  });

  it('refuses a non-absolute path client-side instead of letting the server 422', () => {
    stubUseCase(() => success(matchedFixture));

    render(<RoutingExplorerDemo />);

    fireEvent.change(screen.getByTestId('rx-path'), { target: { value: 'api/health' } });

    expect(screen.getByTestId('rx-path-warning')).toBeInTheDocument();
    expect(screen.getByTestId('rx-match')).toBeDisabled();
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The demo endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-41',
            }),
          )
        : success(matchedFixture);
    });

    render(<RoutingExplorerDemo />);

    fireEvent.click(screen.getByTestId('rx-match'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-fires the same request and the verdict renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('rx-result')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
