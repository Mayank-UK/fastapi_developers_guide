import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import PerfBenchDemo from './bench_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetPerfBenchDemoUseCase } from '../../../domain/demo/get-perf-bench-demo-usecase';
import type { PerfBenchPanel } from '../../../domain/demo/perf-bench';

/**
 * PerfBenchDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the
 * token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * panel renders the measured compression rows, the hygiene pair with its
 * contrast, the introspected loop/pool/GC facts, the collection row, the
 * health receipt, and the honesty note; a failed read degrades to the
 * shared error panel with recovery.
 */

const fakePanel: PerfBenchPanel = {
  compression: [
    {
      payloadId: 'content-index',
      payload: 'GET /api/content — the served topic index (real internal round) — 39 topics, 10 groups',
      level: 1,
      rawBytes: 14468,
      gzippedBytes: 5996,
      savedPercent: 58.6,
      encodeMs: 0.267,
      decodeMs: 0.038,
      iterations: 20,
    },
    {
      payloadId: 'performance-detail',
      payload: 'GET /api/content/performance — this very page\u2019s detail payload',
      level: 6,
      rawBytes: 36706,
      gzippedBytes: 13298,
      savedPercent: 63.8,
      encodeMs: 1.27,
      decodeMs: 0.173,
      iterations: 8,
    },
  ],
  hygiene: [
    {
      label: 'threadpool-offload',
      what: '80ms busy CPU via asyncio.to_thread — the block contained off the loop',
      elapsedMs: 80.3,
      loopLagMaxMs: 5.1,
      concurrentHealthMs: 18.7,
      concurrentHealthStatus: 200,
      verdict: 'The 80ms of CPU contained: health answered mid-block.',
    },
    {
      label: 'on-loop-block',
      what: 'the same 80ms busy CPU run directly on the loop — bounded on purpose',
      elapsedMs: 80.0,
      loopLagMaxMs: 60.2,
      concurrentHealthMs: 80.6,
      concurrentHealthStatus: 200,
      verdict: 'The pathology: one request\u2019s block is every request\u2019s latency.',
    },
  ],
  loop: [
    {
      id: 'loop-class',
      label: 'the event loop serving this request',
      value: 'uvloop.Loop — uvloop is running this very event loop',
    },
  ],
  pool: [
    {
      id: 'pool-status',
      label: "the pool's own status() line (live)",
      value: 'Pool size: 5  Connections in pool: 0 Current Overflow: -5 Current Checked out connections: 0',
    },
  ],
  gcFacts: [
    { id: 'gc-thresholds', label: 'generation thresholds', value: '(2000, 10, 10) — CPython 3.13\u2019s default' },
  ],
  gcCollection: {
    workload: 'gc.collect() — a full collection of every generation',
    elapsedMs: 61.1,
    collected: 30,
    offLoop: true,
    note: 'Measured on this request, run via asyncio.to_thread.',
  },
  healthAfter: { status: 200, elapsedMs: 0.7 },
  honestyNote: 'Every number was measured on this very request.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<PerfBenchPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetPerfBenchDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetPerfBenchDemoUseCase);
}

describe('PerfBenchDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['perf:bench']).toBeDefined();
  });

  it('renders the measured compression rows, hygiene pair, facts, and the receipt', async () => {
    stubUseCase(() => success(fakePanel));

    render(<PerfBenchDemo />);

    await waitFor(() => expect(screen.getByTestId('pbf-panel')).toBeInTheDocument());

    const compression = screen.getByTestId('pbf-compression');
    expect(compression).toHaveTextContent('39 topics, 10 groups');
    expect(screen.getByTestId('pbf-c-content-index-1')).toHaveTextContent('14468');
    expect(screen.getByTestId('pbf-c-content-index-1')).toHaveTextContent('58.6% saved');
    expect(screen.getByTestId('pbf-c-performance-detail-6')).toHaveTextContent('13298');

    const offload = screen.getByTestId('pbf-h-threadpool-offload');
    expect(offload).toHaveTextContent('loop lag max 5.1ms');
    expect(offload).toHaveTextContent('health answered mid-block');
    const onLoop = screen.getByTestId('pbf-h-on-loop-block');
    expect(onLoop).toHaveTextContent('loop lag max 60.2ms');
    expect(onLoop).toHaveTextContent("one request\u2019s block is every request\u2019s latency");

    expect(screen.getByTestId('pbf-f-loop-class')).toHaveTextContent('uvloop.Loop');
    expect(screen.getByTestId('pbf-f-pool-status')).toHaveTextContent('Pool size: 5');
    expect(screen.getByTestId('pbf-f-gc-thresholds')).toHaveTextContent('(2000, 10, 10)');
    expect(screen.getByTestId('pbf-gc-collect')).toHaveTextContent('61.1ms');
    expect(screen.getByTestId('pbf-gc-collect')).toHaveTextContent('off-loop via to_thread');

    expect(screen.getByTestId('pbf-receipt')).toHaveTextContent('200 in 0.7ms');
    expect(screen.getByTestId('pbf-receipt')).toHaveTextContent('the loop never wedged');
    expect(screen.getByTestId('pbf-honesty-note')).toHaveTextContent(
      'measured on this very request',
    );
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The bench did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-perf-bench-1',
            }),
          )
        : success(fakePanel);
    });

    render(<PerfBenchDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('pbf-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
