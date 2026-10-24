import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ReliabilityBreakerDemo from './breaker_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetReliabilityBreakerDemoUseCase } from '../../../domain/demo/get-reliability-breaker-demo-usecase';
import type { BreakerPanel } from '../../../domain/demo/reliability-breaker';

/**
 * ReliabilityBreakerDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the full-cycle state line, the policy facts, all eleven walk
 * rows (trip, fail-fasts, the probe, recovery), the latency contrast,
 * and the honesty note; a failed read degrades to the shared error panel
 * with recovery.
 */

const fakePanel: BreakerPanel = {
  policy: [
    {
      id: 'failure-threshold',
      label: 'consecutive failures that trip open',
      value: '3 — a success resets the count',
    },
    { id: 'open-timeout', label: 'how long open fast-fails', value: '2s (logical, injected clock)' },
    { id: 'half-open-successes', label: 'probe successes that close again', value: '1' },
    {
      id: 'failure-latency',
      label: "the failing dependency's real latency",
      value: '60ms bounded — the cost a fast-failed call never pays',
    },
  ],
  calls: [
    { step: 1, label: 'call while healthy', action: 'call', stateBefore: 'closed', admitted: true, isProbe: false, dependencyTouched: true, outcome: 'success', elapsedMs: 0.1, consecutiveFailures: 0, retryAfterS: null, reason: 'success while closed — the consecutive-failure count resets' },
    { step: 5, label: 'call while the dependency is failing', action: 'call', stateBefore: 'closed', admitted: true, isProbe: false, dependencyTouched: true, outcome: 'failure', elapsedMs: 60.4, consecutiveFailures: 3, retryAfterS: null, reason: '3 consecutive failures reached the threshold of 3 — breaker opens for 2s' },
    { step: 6, label: 'call while the breaker is open', action: 'call', stateBefore: 'open', admitted: false, isProbe: false, dependencyTouched: false, outcome: 'rejected', elapsedMs: 0.0, consecutiveFailures: 3, retryAfterS: 2.0, reason: 'open — fast-fail without touching the dependency; half-open probe allowed in 2.00s' },
    { step: 7, label: 'wait 1s (logical — the injected clock jumps)', action: 'advance-clock', stateBefore: 'open', admitted: null, isProbe: false, dependencyTouched: false, outcome: 'clock-advanced', elapsedMs: 0.0, consecutiveFailures: 3, retryAfterS: 2.0, reason: 'the verdict does not change with the clock alone' },
    { step: 10, label: 'the half-open probe', action: 'call', stateBefore: 'half_open', admitted: true, isProbe: true, dependencyTouched: true, outcome: 'success', elapsedMs: 0.1, consecutiveFailures: 0, retryAfterS: null, reason: 'half-open probe succeeded (1/1 needed) — breaker closes, calls flow again' },
    { step: 11, label: 'call after recovery', action: 'call', stateBefore: 'closed', admitted: true, isProbe: false, dependencyTouched: true, outcome: 'success', elapsedMs: 0.1, consecutiveFailures: 0, retryAfterS: null, reason: 'success while closed — the consecutive-failure count resets' },
  ],
  latency: [
    { id: 'fail-fast', label: 'mean latency of rejected (fail-fast) calls', value: '0.000ms over 2 calls — the dependency was never touched' },
    { id: 'real-failure', label: 'mean latency of real failing calls', value: '60.2ms over 3 calls — the bounded cost of discovering the failure the hard way' },
    { id: 'contrast', label: 'the contrast', value: '2 rejected calls skipped 120ms of wasted dependency time in total' },
  ],
  statesVisited: ['closed', 'open', 'half_open', 'closed'],
  stateLine: 'closed → open → half-open → closed — one full cycle; 2 calls fast-failed without touching the dependency',
  honestyNote: 'Every verdict on this panel was returned by the real CircuitBreaker substrate on this very request, over a fresh instance per run.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<BreakerPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetReliabilityBreakerDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetReliabilityBreakerDemoUseCase);
}

describe('ReliabilityBreakerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['reliability:breaker']).toBeDefined();
  });

  it('renders the state line, policy facts, the walk with its trip and probe, and the latency contrast', async () => {
    stubUseCase(() => success(fakePanel));

    render(<ReliabilityBreakerDemo />);

    await waitFor(() => expect(screen.getByTestId('rlb-panel')).toBeInTheDocument());

    const stateLine = screen.getByTestId('rlb-state-line');
    expect(stateLine).toHaveTextContent('closed → open → half-open → closed');
    expect(stateLine).toHaveTextContent('2 calls fast-failed');

    expect(screen.getByTestId('rlb-f-failure-threshold')).toHaveTextContent('3 — a success resets');
    expect(screen.getByTestId('rlb-f-open-timeout')).toHaveTextContent('injected clock');

    const trip = screen.getByTestId('rlb-c-5');
    expect(trip).toHaveTextContent('fails=3');
    expect(trip).toHaveTextContent('breaker opens for 2s');
    const rejected = screen.getByTestId('rlb-c-6');
    expect(rejected).toHaveTextContent('rejected in 0ms');
    expect(rejected).toHaveTextContent('touched=false');
    expect(rejected).toHaveTextContent('retry in 2s');
    const advance = screen.getByTestId('rlb-c-7');
    expect(advance).toHaveTextContent('the injected clock jumps');
    const probe = screen.getByTestId('rlb-c-10');
    expect(probe).toHaveTextContent('half_open · PROBE');
    expect(probe).toHaveTextContent('breaker closes, calls flow again');
    expect(screen.getByTestId('rlb-c-11')).toHaveTextContent('[closed] success');

    expect(screen.getByTestId('rlb-f-fail-fast')).toHaveTextContent('the dependency was never touched');
    expect(screen.getByTestId('rlb-f-real-failure')).toHaveTextContent('60.2ms');
    expect(screen.getByTestId('rlb-honesty-note')).toHaveTextContent('real CircuitBreaker substrate');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The breaker panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-breaker-1',
            }),
          )
        : success(fakePanel);
    });

    render(<ReliabilityBreakerDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('rlb-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
