import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetArchSagaDemoUseCase } from '../../../domain/demo/get-arch-saga-demo-usecase';
import type {
  ArchSagaPanel,
  SagaBalanceRow,
  SagaDurabilityRow,
  SagaRunRow,
} from '../../../domain/demo/arch-saga';

/**
 * ArchSagaDemo — the advanced-architecture topic's live saga panel
 * (demo block id `arch:saga`). One read where the server drove the
 * REAL SagaCoordinator through both of a saga's lives over a scratch
 * ledger: the committed four-step run, then the failing run whose
 * compensations unwound the completed steps in REVERSE order with
 * per-step evidence — and the balance rows proving the undo returned
 * every metric to its starting value.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: ArchSagaPanel };

function outcomeTone(outcome: string): string {
  if (outcome === 'committed' || outcome === 'done') return 'text-primary';
  if (outcome === 'failed' || outcome === 'compensation-failed') return 'text-error';
  return 'text-on-surface-variant';
}

function RunBlock({ title, run }: { title: string; run: SagaRunRow }) {
  return (
    <section
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      data-testid={`asg-run-${run.outcome}`}
    >
      <p className="text-caption text-on-surface">
        <span className="font-mono text-primary">{title}</span>{' '}
        <span className={outcomeTone(run.outcome)}>[{run.outcome}]</span>{' '}
        <span className="text-on-surface-variant">{run.label}</span>
      </p>
      {run.entries.map((entry) => (
        <p
          key={`${entry.phase}-${entry.step}`}
          className="font-mono text-caption text-on-surface"
          data-testid={`asg-e-${run.outcome}-${entry.step}`}
        >
          {entry.at} <span className={outcomeTone(entry.outcome)}>{entry.phase}</span>{' '}
          {entry.step} — <span className="text-on-surface-variant">{entry.evidence}</span>
        </p>
      ))}
      {run.failureStep && (
        <p className="font-mono text-caption text-on-surface" data-testid="asg-undo-order">
          undo order:{' '}
          <span className="text-primary">{run.compensationOrder.join(' -> ')}</span>
        </p>
      )}
      <p className="text-caption text-on-surface-variant">{run.detail}</p>
    </section>
  );
}

function BalanceLine({ row }: { row: SagaBalanceRow }) {
  return (
    <p
      className="font-mono text-caption text-on-surface"
      data-testid={`asg-b-${row.metric.replace(/[^a-z]/gi, '')}`}
    >
      {row.metric}: {row.before} → {row.afterHappy} (happy) →{' '}
      <span className="text-primary">{row.afterFailure}</span> (failed) —{' '}
      <span className="text-on-surface-variant">{row.verdict}</span>
    </p>
  );
}

function DurabilityLine({ row }: { row: SagaDurabilityRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`asg-d-${row.half.replace(/\s+/g, '-')}`}>
      <span className="text-primary">{row.half}</span> — {row.what}.{' '}
      <span className="text-on-surface-variant">({row.where})</span>
    </p>
  );
}

export default function ArchSagaDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetArchSagaDemoUseCase = container.getArchSagaDemoUseCase;
    const result: Result<ArchSagaPanel> = await useCase.saga();
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
    return <p data-testid="asg-loading">Running the saga both ways…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the saga panel"
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
    <section className="flex flex-col gap-sm" data-testid="asg-panel">
      <section className="flex flex-col gap-xxs" data-testid="asg-workflow">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">{data.workflow.name}</span>{' '}
          <span className="text-on-surface-variant">
            four steps, each naming its undo before it runs
          </span>
        </p>
        {data.workflow.steps.map((step) => (
          <p
            key={step.action}
            className="font-mono text-caption text-on-surface"
            data-testid={`asg-s-${step.action}`}
          >
            {step.action}{' '}
            <span className="text-on-surface-variant">
              (undo: {step.compensates}) — {step.describes}
            </span>
          </p>
        ))}
      </section>

      <RunBlock title="Run 1" run={data.happyRun} />
      <RunBlock title="Run 2" run={data.failureRun} />

      <section className="flex flex-col gap-xxs" data-testid="asg-balances">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The undo's arithmetic</span>{' '}
          <span className="text-on-surface-variant">
            every metric returns to its start after compensation
          </span>
        </p>
        {data.balances.map((row) => (
          <BalanceLine key={row.metric} row={row} />
        ))}
      </section>

      <section className="flex flex-col gap-xxs" data-testid="asg-durability">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Durability in production</span>{' '}
          <span className="text-on-surface-variant">
            the two halves a durable runner adds around this coordinator
          </span>
        </p>
        {data.durability.map((row) => (
          <DurabilityLine key={row.half} row={row} />
        ))}
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="asg-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
