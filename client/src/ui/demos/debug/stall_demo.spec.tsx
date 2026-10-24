import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DebugStallDemo from './stall_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDebugStallDemoUseCase } from '../../../domain/demo/get-debug-stall-demo-usecase';
import type { StallPanel } from '../../../domain/demo/debug-stall';

/**
 * DebugStallDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the
 * token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * panel renders the four phases with their measured evidence, the
 * tracemalloc row, this request's correlated log rows, and the honest
 * tooling notes; a failed read degrades to the shared error panel with
 * recovery.
 */

const fakePanel: StallPanel = {
  panelRequestId: 'stall-panel-id-42',
  phases: [
    {
      label: 'baseline',
      what: 'one scheduler yield (await asyncio.sleep(0)) — the unit of comparison',
      elapsedMs: 0.6,
      loopLagMaxMs: 1.1,
      loopLagMeanMs: 0.5,
      concurrentHealthMs: 3.2,
      concurrentHealthStatus: 200,
      verdict: 'The unit of comparison: one scheduler yield, sub-millisecond everything.',
    },
    {
      label: 'async-await-stall',
      what: 'await asyncio.sleep(0.35) — slow request, free loop',
      elapsedMs: 350.7,
      loopLagMaxMs: 2.0,
      loopLagMeanMs: 0.4,
      concurrentHealthMs: 2.1,
      concurrentHealthStatus: 200,
      verdict: 'Slow request, HEALTHY loop: the 350ms is awaiting, not CPU.',
    },
    {
      label: 'blocking-in-threadpool',
      what: '120ms busy CPU via asyncio.to_thread — the block contained off the loop',
      elapsedMs: 131.1,
      loopLagMaxMs: 5.5,
      loopLagMeanMs: 4.4,
      concurrentHealthMs: 27.5,
      concurrentHealthStatus: 200,
      verdict: '120ms of real CPU, contained: asyncio.to_thread moved the block off the loop.',
    },
    {
      label: 'blocking-on-loop',
      what: 'the same 120ms busy CPU run directly on the loop — the starvation made visible',
      elapsedMs: 120.0,
      loopLagMaxMs: 96.4,
      loopLagMeanMs: 25.0,
      concurrentHealthMs: 123.1,
      concurrentHealthStatus: 200,
      verdict: 'The pathology: one request’s block is every request’s latency.',
    },
  ],
  allocations: {
    workload: '2000 small dict rows (a parsed-JSON shape) built while tracemalloc watched',
    objects: 2000,
    currentKb: 691.2,
    peakKb: 691.3,
    note: 'tracemalloc is stdlib and this window is real.',
  },
  logEvents: [
    {
      sequence: 30,
      level: 'info',
      event: 'debug_stall_phase',
      requestId: 'stall-panel-id-42',
      timestamp: '2026-10-24T08:00:00Z',
      fields: [
        { name: 'concurrent_health_ms', value: '2.1' },
        { name: 'elapsed_ms', value: '350.7' },
      ],
    },
  ],
  pySpyNote: 'py-spy is NOT installed in this repo — no dependency was added for this topic.',
  honestyNote: 'Every number is measured on this very request.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<StallPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDebugStallDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetDebugStallDemoUseCase);
}

describe('DebugStallDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['debug:stall']).toBeDefined();
  });

  it('renders the four phases with their measured evidence', async () => {
    stubUseCase(() => success(fakePanel));

    render(<DebugStallDemo />);

    await waitFor(() => expect(screen.getByTestId('ds-panel')).toBeInTheDocument());
    expect(screen.getByTestId('ds-root')).toHaveTextContent('stall-panel-id-42');

    const stall = screen.getByTestId('ds-phase-async-await-stall');
    expect(stall).toHaveTextContent('elapsed 350.7ms');
    expect(stall).toHaveTextContent('health 2.1ms/200');
    expect(stall).toHaveTextContent('HEALTHY loop');

    const onLoop = screen.getByTestId('ds-phase-blocking-on-loop');
    expect(onLoop).toHaveTextContent('lagMax 96.4ms');
    expect(onLoop).toHaveTextContent('health 123.1ms/200');

    expect(screen.getByTestId('ds-alloc')).toHaveTextContent('2000 objects');
    expect(screen.getByTestId('ds-alloc')).toHaveTextContent('peak 691.3KB');
    expect(screen.getByTestId('ds-logs')).toHaveTextContent('debug_stall_phase');
    expect(screen.getByTestId('ds-logs')).toHaveTextContent('elapsed_ms=350.7');
    expect(screen.getByTestId('ds-pyspy-note')).toHaveTextContent('NOT installed');
    expect(screen.getByTestId('ds-honesty-note')).toHaveTextContent('measured on this very request');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The stall panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-debug-stall-1',
            }),
          )
        : success(fakePanel);
    });

    render(<DebugStallDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('ds-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
