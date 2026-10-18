import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RuntimeAsyncDemo } from './async_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetRuntimeAsyncDemoUseCase } from '../../../domain/demo/get-runtime-async-demo-usecase';
import type { RuntimeAsyncDemoData } from '../../../domain/demo/runtime-async';

/**
 * RuntimeAsyncDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam) instead
 * of stubbing fetch. Behavior, not implementation: the measured numbers,
 * both runs' completion orders, and the interleaving trace render, and
 * failures degrade to the shared error panel with recovery.
 */

const fixture: RuntimeAsyncDemoData = {
  ioPlan: [
    { name: 'orders', simulatedIoMs: 60 },
    { name: 'billing', simulatedIoMs: 40 },
    { name: 'inventory', simulatedIoMs: 20 },
  ],
  sequential: {
    strategy: 'sequential',
    elapsedMs: 120.44,
    completionOrder: ['orders', 'billing', 'inventory'],
    perTask: [
      { name: 'orders', simulatedIoMs: 60, measuredMs: 60.12 },
      { name: 'billing', simulatedIoMs: 40, measuredMs: 40.09 },
      { name: 'inventory', simulatedIoMs: 20, measuredMs: 20.05 },
    ],
  },
  gathered: {
    strategy: 'gathered',
    elapsedMs: 60.21,
    completionOrder: ['inventory', 'billing', 'orders'],
    perTask: [
      { name: 'orders', simulatedIoMs: 60, measuredMs: 60.18 },
      { name: 'billing', simulatedIoMs: 40, measuredMs: 40.03 },
      { name: 'inventory', simulatedIoMs: 20, measuredMs: 20.02 },
    ],
  },
  speedup: 2.0,
  trace: [
    { actor: 'alpha', event: 'start' },
    { actor: 'beta', event: 'start' },
    { actor: 'alpha', event: 'step-0' },
    { actor: 'beta', event: 'step-0' },
    { actor: 'alpha', event: 'step-1' },
    { actor: 'beta', event: 'step-1' },
    { actor: 'alpha', event: 'step-2' },
    { actor: 'beta', event: 'step-2' },
    { actor: 'alpha', event: 'done' },
    { actor: 'beta', event: 'done' },
  ],
};

function stubUseCase(execute: () => Promise<Result<RuntimeAsyncDemoData>>): void {
  container.initialize(createAppConfig());
  container.register(
    ContainerTokens.GetRuntimeAsyncDemoUseCase,
    { execute } as unknown as GetRuntimeAsyncDemoUseCase,
  );
}

describe('RuntimeAsyncDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['runtime:async']).toBeDefined();
  });

  it('renders loading first, then the measurement faces', async () => {
    stubUseCase(async () => success(fixture));

    render(<RuntimeAsyncDemo />);

    expect(screen.getByTestId('runtime-async-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('ra-speedup')).toBeInTheDocument());

    // Headline numbers: both measurements and the honest ratio.
    expect(screen.getByTestId('ra-sequential-ms')).toHaveTextContent('120.4 ms');
    expect(screen.getByTestId('ra-gathered-ms')).toHaveTextContent('60.2 ms');
    expect(screen.getByTestId('ra-speedup-value')).toHaveTextContent('2.00');

    // Both runs render with their (different) completion orders.
    expect(screen.getByTestId('ra-sequential')).toHaveTextContent(
      'orders → billing → inventory',
    );
    expect(screen.getByTestId('ra-gathered')).toHaveTextContent(
      'inventory → billing → orders',
    );
    expect(screen.getByTestId('ra-gathered')).toHaveTextContent('60.2 ms');

    // The trace: every interleaved event, alternation visible.
    const trace = screen.getByTestId('ra-trace-events');
    expect(trace).toHaveTextContent('alpha:start');
    expect(trace).toHaveTextContent('beta:step-2');
    expect(trace).toHaveTextContent('alpha:done');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The demo endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-32',
            }),
          )
        : success(fixture);
    });

    render(<RuntimeAsyncDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-runs the measurement and the payload renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('ra-speedup')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
