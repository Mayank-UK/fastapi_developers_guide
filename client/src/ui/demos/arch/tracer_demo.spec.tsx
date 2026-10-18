import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ArchTracerDemo } from './tracer_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetArchTracerDemoUseCase } from '../../../domain/demo/get-arch-tracer-demo-usecase';
import type { ArchTracerData } from '../../../domain/demo/arch-tracer';

/**
 * ArchTracerDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the button
 * fires one trace, the payload renders the wiring card, the live stack
 * with kind chips, both measured rounds with their beats, facts, and
 * evidence-labeled hops; failures degrade to the shared error panel with
 * recovery.
 */

const fixture: ArchTracerData = {
  stack: [
    {
      name: 'ServerErrorMiddleware',
      kind: 'framework',
      orderIndex: 0,
      role: "Starlette's outermost bookend — where the last-resort 500 handler runs.",
    },
    {
      name: 'RequestIdMiddleware',
      kind: 'user',
      orderIndex: 4,
      role: 'the request-id layer — assigns request-side, stamps the header response-side.',
    },
    {
      name: 'APIRouter',
      kind: 'router',
      orderIndex: 7,
      role: 'the terminal ASGI app — routing, dependencies, the endpoint.',
    },
  ],
  route: {
    template: '/api/posts',
    method: 'GET',
    endpoint: 'list_posts',
    responseModel: 'PostPage',
    dependencies: [
      { param: 'query', provider: 'PostListQuery', providerKind: 'model' },
      { param: 'use_cases', provider: 'get_post_use_cases', providerKind: 'function' },
    ],
  },
  wiring: {
    port: 'PostRepository',
    adapter: 'InMemoryPostRepository',
    useCases: 'PostUseCases',
    wiredBy: 'create_app()',
  },
  rounds: [
    {
      outcome: 'ok',
      requestLine: 'GET /api/posts?page=2&limit=4',
      inboundRequestId: 'arch-tracer-ok-round',
      status: 200,
      beats: [
        { event: 'enter', offsetMs: 0 },
        { event: 'response.start', offsetMs: 1.5 },
        { event: 'complete', offsetMs: 1.5 },
      ],
      facts: [
        { name: 'status', value: '200' },
        { name: 'inboundIdEchoed', value: 'true' },
      ],
      hops: [
        {
          stage: 'middleware stack',
          layer: 'presentation.middleware',
          detail: 'the inbound x-request-id was accepted and echoed back.',
          evidence: 'observed',
        },
        {
          stage: 'repository',
          layer: 'data.adapter',
          detail: 'the adapter behind the port: filter, sort, count, slice.',
          evidence: 'observed',
        },
      ],
    },
    {
      outcome: 'err',
      requestLine: 'GET /api/posts/nope',
      inboundRequestId: 'arch-tracer-err-round',
      status: 404,
      beats: [
        { event: 'enter', offsetMs: 0 },
        { event: 'response.start', offsetMs: 0.6 },
        { event: 'complete', offsetMs: 0.6 },
      ],
      facts: [
        { name: 'envelope code', value: 'not_found' },
        { name: 'headerMatchesBody', value: 'true' },
      ],
      hops: [
        {
          stage: 'use case',
          layer: 'domain.use-cases',
          detail: 'None became Err(AppError(not_found)) — a domain answer.',
          evidence: 'introspected',
        },
        {
          stage: 'exception handler',
          layer: 'core.errors',
          detail: 'the shared handler rendered the 404 envelope with the id.',
          evidence: 'observed',
        },
      ],
    },
  ],
  reasoning: 'Only the boundary beats are measured; every hop labels its evidence.',
};

/** Swap the container's use-case token for a stub answering `respond`. */
function stubUseCase(respond: () => Result<ArchTracerData>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetArchTracerDemoUseCase, {
    execute: () => Promise.resolve(respond()),
  } as unknown as GetArchTracerDemoUseCase);
}

describe('ArchTracerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['arch:tracer']).toBeDefined();
  });

  it('starts idle and renders wiring, stack, and both rounds on run', async () => {
    stubUseCase(() => success(fixture));

    render(<ArchTracerDemo />);

    expect(screen.getByTestId('at-idle')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('at-run'));

    await waitFor(() => expect(screen.getByTestId('at-result')).toBeInTheDocument());
    expect(screen.getByTestId('at-wiring')).toHaveTextContent('InMemoryPostRepository');
    expect(screen.getByTestId('at-wiring')).toHaveTextContent('PostRepository');
    expect(screen.getByTestId('at-wiring')).toHaveTextContent('list_posts');
    expect(screen.getByTestId('at-wiring')).toHaveTextContent('get_post_use_cases');
    expect(screen.getByTestId('at-stack')).toHaveTextContent('RequestIdMiddleware');
    expect(screen.getByTestId('at-stack')).toHaveTextContent('user');
    expect(screen.getByTestId('at-stack')).toHaveTextContent('router');
    expect(screen.getByTestId('at-round-ok')).toHaveTextContent('GET /api/posts?page=2&limit=4');
    expect(screen.getByTestId('at-round-ok')).toHaveTextContent('200');
    expect(screen.getByTestId('at-round-ok')).toHaveTextContent('response.start@1.5ms');
    expect(screen.getByTestId('at-round-err')).toHaveTextContent('GET /api/posts/nope');
    expect(screen.getByTestId('at-round-err')).toHaveTextContent('404');
    expect(screen.getByTestId('at-round-err')).toHaveTextContent('headerMatchesBody: true');
    expect(screen.getByTestId('at-reasoning')).toHaveTextContent('labels its evidence');
  });

  it('fires exactly one trace per click and shows evidence chips on hops', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return success(fixture);
    });

    render(<ArchTracerDemo />);

    fireEvent.click(screen.getByTestId('at-run'));

    await waitFor(() => expect(screen.getByTestId('at-result')).toBeInTheDocument());
    expect(calls).toBe(1);
    expect(screen.getByTestId('at-round-ok')).toHaveTextContent('observed');
    expect(screen.getByTestId('at-round-err')).toHaveTextContent('introspected');
  });

  it('degrades to the shared error panel with recovery on a Failed Result', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The tracer round-trip failed.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-42',
            }),
          )
        : success(fixture);
    });

    render(<ArchTracerDemo />);

    fireEvent.click(screen.getByTestId('at-run'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('The tracer round-trip failed.');
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-fires and the tracer renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('at-result')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
