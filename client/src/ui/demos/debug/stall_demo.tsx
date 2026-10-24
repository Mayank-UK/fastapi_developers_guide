import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetDebugStallDemoUseCase } from '../../../domain/demo/get-debug-stall-demo-usecase';
import type { StallPanel, StallPhase } from '../../../domain/demo/debug-stall';

/**
 * DebugStallDemo — the debugging topic's stall diagnosis (demo block id
 * `debug:stall`). One live read where the server ran four bounded phases
 * — a baseline yield, a 350ms async await, a 120ms CPU block contained in
 * a threadpool, and the SAME block run directly on the event loop — and
 * measured each: elapsed, loop lag from a concurrent probe's sleep
 * overshoot, and a REAL internal /api/health driven through the app
 * mid-phase. The read that matters: the async phase is the slowest yet
 * its concurrent health answers fastest (slow request, healthy loop),
 * while the on-loop block starves the lag probe and makes health wait
 * out the whole block — the classification a sampling profiler would
 * give from outside, with every duration bounded so the shared loop is
 * never wedged.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: StallPanel };

function phaseTone(phase: StallPhase): string {
  if (phase.label === 'blocking-on-loop') return 'text-error';
  if (phase.label === 'async-await-stall') return 'text-warning';
  return 'text-primary';
}

function Phase({ phase }: { phase: StallPhase }) {
  return (
    <section
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      data-testid={`ds-phase-${phase.label}`}
    >
      <p className="font-mono text-caption text-on-surface">
        <span className={phaseTone(phase)}>{phase.label}</span>{' '}
        <span className="text-on-surface-variant">
          elapsed {phase.elapsedMs}ms · lagMax {phase.loopLagMaxMs}ms · health{' '}
          {phase.concurrentHealthMs}ms/{phase.concurrentHealthStatus}
        </span>
      </p>
      <p className="text-caption text-on-surface-variant">{phase.what}</p>
      <p className="text-caption text-on-surface">{phase.verdict}</p>
    </section>
  );
}

export default function DebugStallDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetDebugStallDemoUseCase = container.getDebugStallDemoUseCase;
    const result: Result<StallPanel> = await useCase.panel();
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
    return <p data-testid="ds-loading">Running the four bounded phases…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the stall diagnosis"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;
  const allocations = data.allocations;

  return (
    <section className="flex flex-col gap-sm" data-testid="ds-panel">
      <header className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs">
        <p className="font-mono text-caption text-primary" data-testid="ds-root">
          panel request {data.panelRequestId}
        </p>
      </header>

      {data.phases.map((phase) => (
        <Phase key={phase.label} phase={phase} />
      ))}

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="ds-alloc"
      >
        <p className="font-mono text-caption text-on-surface">
          tracemalloc · {allocations.objects} objects · current {allocations.currentKb}KB · peak{' '}
          {allocations.peakKb}KB
        </p>
        <p className="text-caption text-on-surface-variant">{allocations.note}</p>
      </section>

      <section className="flex flex-col gap-xxs" data-testid="ds-logs">
        {data.logEvents.map((event) => (
          <p key={event.sequence} className="font-mono text-caption text-on-surface">
            <span className="text-on-surface-variant">[{event.level}]</span> {event.event}{' '}
            <span className="text-on-surface-variant">
              {event.fields.map((field) => `${field.name}=${field.value}`).join(' ')}
            </span>
          </p>
        ))}
      </section>

      <p className="text-caption text-on-surface" data-testid="ds-pyspy-note">
        {data.pySpyNote}
      </p>
      <p className="text-caption text-on-surface-variant" data-testid="ds-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
