import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetReliabilityBreakerDemoUseCase } from '../../../domain/demo/get-reliability-breaker-demo-usecase';
import type {
  BreakerCallRow,
  BreakerFactRow,
  BreakerPanel,
} from '../../../domain/demo/reliability-breaker';

/**
 * ReliabilityBreakerDemo — the reliability topic's live circuit breaker
 * (demo block id `reliability:breaker`). One read where the server walks
 * the REAL pure CircuitBreaker substrate through a full cycle on the very
 * request that serves it: healthy calls while closed, three consecutive
 * failures that trip the breaker open, calls rejected FAST (dependency
 * never touched, ~0ms), the open timeout elapsing on an injected clock,
 * one half-open probe, recovery to closed. Every row shows the state at
 * acquire, the measured latency, the consecutive-failure count, and the
 * substrate's own reason string.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: BreakerPanel };

function outcomeTone(row: BreakerCallRow): string {
  if (row.outcome === 'rejected') return 'text-error';
  if (row.outcome === 'failure') return 'text-error';
  if (row.isProbe) return 'text-primary';
  return 'text-on-surface';
}

function CallRow({ row }: { row: BreakerCallRow }) {
  if (row.action === 'advance-clock') {
    return (
      <p className="font-mono text-caption text-on-surface-variant" data-testid={`rlb-c-${row.step}`}>
        {row.step}. {row.label} — {row.stateBefore} → {row.outcome}
      </p>
    );
  }
  const probe = row.isProbe ? ' · PROBE' : '';
  const retryAfter = row.retryAfterS !== null ? ` · retry in ${row.retryAfterS}s` : '';
  return (
    <p className={`font-mono text-caption ${outcomeTone(row)}`} data-testid={`rlb-c-${row.step}`}>
      {row.step}. [{row.stateBefore}
      {probe}] {row.outcome} in {row.elapsedMs}ms · touched={String(row.dependencyTouched)} ·
      fails={row.consecutiveFailures}
      {retryAfter} — {row.reason}
    </p>
  );
}

function FactItem({ row }: { row: BreakerFactRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`rlb-f-${row.id}`}>
      <span className="text-on-surface-variant">{row.label}:</span> {row.value}
    </p>
  );
}

export default function ReliabilityBreakerDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetReliabilityBreakerDemoUseCase = container.getReliabilityBreakerDemoUseCase;
    const result: Result<BreakerPanel> = await useCase.panel();
    if (result.ok) {
      setPanel({ state: 'ready', data: result.value });
    } else {
      setPanel({ state: 'failed', failure: result.failure });
    }
  }, []);

  useEffect(() => {
    void loadPanel();
  }, [loadPanel]);

  if (panel.state === 'loading') {
    return <p data-testid="rlb-loading">Walking the breaker through one full cycle…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the circuit breaker"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;

  return (
    <section className="flex flex-col gap-sm" data-testid="rlb-panel">
      <p className="font-mono text-caption text-primary" data-testid="rlb-state-line">
        {data.stateLine}
      </p>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="rlb-policy"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Policy</span>{' '}
          <span className="text-on-surface-variant">the knobs of this walk, fresh breaker per run</span>
        </p>
        {data.policy.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
      </section>

      <section className="flex flex-col gap-xxs" data-testid="rlb-calls">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The walk</span>{' '}
          <span className="text-on-surface-variant">
            eleven steps, every verdict the real substrate returned
          </span>
        </p>
        {data.calls.map((row) => (
          <CallRow key={row.step} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="rlb-latency"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Latency evidence</span>{' '}
          <span className="text-on-surface-variant">computed from the measured rows, never asserted</span>
        </p>
        {data.latency.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="rlb-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
