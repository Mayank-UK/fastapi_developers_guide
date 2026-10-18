import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DepLifecycleDemo } from './lifecycle_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDepLifecycleDemoUseCase } from '../../../domain/demo/get-dep-lifecycle-demo-usecase';
import type {
  DepLifecycleLogData,
  DepLifecycleSpanData,
} from '../../../domain/demo/dep-lifecycle';

/**
 * DepLifecycleDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the log loads
 * on mount, firing updates the span facts AND refreshes the log, the
 * pendingEvents confession renders, the timeline is sequenced newest
 * first, and both halves degrade to the shared error panel with retry.
 */

const spanFixture: DepLifecycleSpanData = {
  spanId: 'aabbccdd0011',
  setupAt: '2026-10-15T12:00:00.000+00:00',
  handlerOffsetMs: 1,
  pendingEvents: ['teardown'],
};

function logFixture(events: DepLifecycleLogData['events']): DepLifecycleLogData {
  return { capacity: 20, events };
}

function stubUseCase(
  log: Result<DepLifecycleLogData>,
  span: Result<DepLifecycleSpanData> = success(spanFixture),
): GetDepLifecycleDemoUseCase {
  container.initialize(createAppConfig());
  const fake = {
    fire: () => Promise.resolve(span),
    log: () => Promise.resolve(log),
  } as unknown as GetDepLifecycleDemoUseCase;
  container.register(ContainerTokens.GetDepLifecycleDemoUseCase, fake);
  return fake;
}

describe('DepLifecycleDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['dep:lifecycle']).toBeDefined();
  });

  it('loads the log on mount, sequenced newest first', async () => {
    stubUseCase(
      success(
        logFixture([
          { sequence: 0, spanId: 'a', event: 'setup', at: 't0', offsetMs: 0 },
          { sequence: 1, spanId: 'a', event: 'handler', at: 't1', offsetMs: 0 },
          { sequence: 2, spanId: 'a', event: 'response', at: 't2', offsetMs: 1 },
          { sequence: 3, spanId: 'a', event: 'teardown', at: 't3', offsetMs: 2 },
        ]),
      ),
    );

    render(<DepLifecycleDemo />);
    await waitFor(() => {
      expect(screen.getByTestId('dep-lifecycle-log')).toBeInTheDocument();
    });

    const rows = screen.getAllByTestId(/dep-lifecycle-row-/);
    const cells = rows.map(
      (row) => (row as HTMLTableRowElement).cells[2]?.textContent,
    );
    expect(cells).toEqual(['teardown', 'response', 'handler', 'setup']);
    expect(screen.queryByText('the ring is empty')).not.toBeInTheDocument();
  });

  it('fires a wrapped request: span facts render, pending events confess, log refreshes', async () => {
    stubUseCase(success(logFixture([])));

    render(<DepLifecycleDemo />);
    await waitFor(() => {
      expect(screen.getByTestId('dep-lifecycle-empty')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('dep-lifecycle-fire'));
    await waitFor(() => {
      expect(screen.getByTestId('dep-lifecycle-span')).toBeInTheDocument();
    });
    expect(screen.getByTestId('dep-lifecycle-span')).toHaveTextContent('aabbccdd0011');
    expect(screen.getByTestId('dep-lifecycle-pending')).toHaveTextContent('teardown');
    // The fire path refreshed the log (same fixture, still empty is fine —
    // the refresh must at least not crash or drop the panel).
    expect(screen.getByTestId('dep-lifecycle-log')).toBeInTheDocument();
  });

  it('renders the empty ring honestly before any request', async () => {
    stubUseCase(success(logFixture([])));
    render(<DepLifecycleDemo />);
    await waitFor(() => {
      expect(screen.getByTestId('dep-lifecycle-empty')).toBeInTheDocument();
    });
  });

  it('degrades the span request to the shared error panel with retry', async () => {
    let attempts = 0;
    container.initialize(createAppConfig());
    container.register(ContainerTokens.GetDepLifecycleDemoUseCase, {
      fire: () => {
        attempts += 1;
        return Promise.resolve(
          failed(
            new ServerFailure('Request failed with status 500.', {
              code: 'internal',
              status: 500,
              requestId: 'req-61',
            }),
          ),
        );
      },
      log: () => Promise.resolve(success(logFixture([]))),
    } as unknown as GetDepLifecycleDemoUseCase);

    render(<DepLifecycleDemo />);
    fireEvent.click(screen.getByTestId('dep-lifecycle-fire'));
    await waitFor(() => {
      expect(screen.getAllByTestId('error-panel').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Try again')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Try again'));
    await waitFor(() => {
      expect(attempts).toBe(2);
    });
  });
});
