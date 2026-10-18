import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MiddlewarePipelineDemo } from './pipeline_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetMiddlewarePipelineDemoUseCase } from '../../../domain/demo/get-middleware-pipeline-demo-usecase';
import type { MiddlewarePipelineData } from '../../../domain/demo/middleware-pipeline';

/**
 * MiddlewarePipelineDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec swaps
 * the token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * button fires one read, the payload renders its live stack with kind
 * chips, the trace timeline with its three phases, both side orders, and
 * the request-id card; failures degrade to the shared error panel with
 * recovery.
 */

const fixture: MiddlewarePipelineData = {
  stack: [
    {
      name: 'ServerErrorMiddleware',
      kind: 'framework',
      orderIndex: 0,
      role: "Starlette's outermost bookend — the last-resort 500 handler.",
    },
    {
      name: 'RequestIdMiddleware',
      kind: 'user',
      orderIndex: 2,
      role: "this app's request-id layer — assigns request-side, stamps response-side.",
    },
    {
      name: 'APIRouter',
      kind: 'router',
      orderIndex: 5,
      role: 'the terminal ASGI app — routing, dependencies, the endpoint.',
    },
  ],
  trace: [
    { stage: 'ServerErrorMiddleware', phase: 'request', sequence: 0, note: 'descends' },
    { stage: 'RequestIdMiddleware', phase: 'request', sequence: 1, note: 'descends' },
    { stage: 'APIRouter', phase: 'handler', sequence: 2, note: 'endpoint runs once' },
    { stage: 'RequestIdMiddleware', phase: 'response', sequence: 3, note: 'ascends' },
    { stage: 'ServerErrorMiddleware', phase: 'response', sequence: 4, note: 'ascends' },
  ],
  requestSideOrder: ['ServerErrorMiddleware', 'RequestIdMiddleware', 'APIRouter'],
  responseSideOrder: ['APIRouter', 'RequestIdMiddleware', 'ServerErrorMiddleware'],
  requestId: 'ui-probe-11',
  requestIdHeader: 'x-request-id',
  reasoning: 'Request events descend; response events unwind in reverse.',
};

/** Count executions, answering with a fixture (or a Failed Result). */
function stubUseCase(respond: () => Result<MiddlewarePipelineData>): number {
  let calls = 0;
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetMiddlewarePipelineDemoUseCase, {
    execute: () => {
      calls += 1;
      return Promise.resolve(respond());
    },
  } as unknown as GetMiddlewarePipelineDemoUseCase);
  return calls;
}

describe('MiddlewarePipelineDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['middleware:pipeline']).toBeDefined();
  });

  it('starts idle and renders the live stack, trace, orders, and id on run', async () => {
    stubUseCase(() => success(fixture));

    render(<MiddlewarePipelineDemo />);

    expect(screen.getByTestId('mp-idle')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('mp-run'));

    await waitFor(() => expect(screen.getByTestId('mp-result')).toBeInTheDocument());
    expect(screen.getByTestId('mp-stack')).toHaveTextContent('RequestIdMiddleware');
    expect(screen.getByTestId('mp-stack')).toHaveTextContent('user');
    expect(screen.getByTestId('mp-stack')).toHaveTextContent('router');
    expect(screen.getByTestId('mp-trace')).toHaveTextContent('handler');
    expect(screen.getByTestId('mp-trace')).toHaveTextContent('response');
    expect(screen.getByTestId('mp-orders')).toHaveTextContent('request side');
    expect(screen.getByTestId('mp-orders')).toHaveTextContent('response side');
    expect(screen.getByTestId('mp-request-id')).toHaveTextContent('x-request-id');
    expect(screen.getByTestId('mp-request-id')).toHaveTextContent('ui-probe-11');
    expect(screen.getByTestId('mp-reasoning')).toHaveTextContent('unwind in reverse');
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
              requestId: 'req-42',
            }),
          )
        : success(fixture);
    });

    render(<MiddlewarePipelineDemo />);

    fireEvent.click(screen.getByTestId('mp-run'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-fires and the pipeline renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('mp-result')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
