import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RuntimeStreamingDemo } from './streaming_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetRuntimeStreamingDemoUseCase } from '../../../domain/demo/get-runtime-streaming-demo-usecase';
import type {
  RuntimeStreamingDemoData,
  StreamChunk,
} from '../../../domain/demo/runtime-streaming';

/**
 * RuntimeStreamingDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container (the token-swap seam), renders
 * each stream line it is handed, and finishes on the closing line with the
 * delivered count and measured total. Failures degrade to the shared error
 * panel with recovery.
 */

const chunks: StreamChunk[] = [
  {
    seq: 0,
    kind: 'open',
    label: 'runtime-stream',
    detail: '6 items follow, one per awaited tick',
  },
  ...[1, 2, 3, 4, 5, 6].map(
    (index): StreamChunk => ({
      seq: index,
      kind: 'item',
      label: `loop-tick-${String(index)}`,
      detail: 'yielded after 2ms of simulated io',
    }),
  ),
  { seq: 7, kind: 'closed', label: 'stream-complete', itemsDelivered: 6, totalMs: 15.3 },
];

const fixture: RuntimeStreamingDemoData = { chunks };

function stubUseCase(
  execute: (onChunk?: (chunk: StreamChunk) => void) => Promise<Result<RuntimeStreamingDemoData>>,
): void {
  container.initialize(createAppConfig());
  container.register(
    ContainerTokens.GetRuntimeStreamingDemoUseCase,
    { execute } as unknown as GetRuntimeStreamingDemoUseCase,
  );
}

describe('RuntimeStreamingDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['runtime:streaming']).toBeDefined();
  });

  it('renders loading first, then every line and the closing summary', async () => {
    // The observer replays arrival order (after a microtask hop, so the
    // loading state paints first, as with a real wire); the Result settles.
    stubUseCase(async (onChunk) => {
      await Promise.resolve();
      for (const chunk of chunks) onChunk?.(chunk);
      return success(fixture);
    });

    render(<RuntimeStreamingDemo />);

    expect(screen.getByTestId('runtime-streaming-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('rs-status')).toBeInTheDocument());

    // All eight lines render, in order, with their labels.
    for (const chunk of chunks) {
      expect(screen.getByTestId(`rs-line-${String(chunk.seq)}`)).toHaveTextContent(
        chunk.label,
      );
    }
    expect(screen.getByTestId('rs-line-count')).toHaveTextContent('8');

    // The closing summary: measured count and measured milliseconds.
    expect(screen.getByTestId('rs-closed')).toHaveTextContent('6 items delivered');
    expect(screen.getByTestId('rs-closed')).toHaveTextContent('15.3 ms');
    expect(screen.getByTestId('rs-status')).toHaveTextContent('Stream complete');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The stream could not be opened.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-33',
            }),
          )
        : success(fixture);
    });

    render(<RuntimeStreamingDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-opens the stream and the lines render.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('rs-line-7')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
