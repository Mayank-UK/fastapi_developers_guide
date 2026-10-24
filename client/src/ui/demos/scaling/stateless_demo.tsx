import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetScalingStatelessDemoUseCase } from '../../../domain/demo/get-scaling-stateless-demo-usecase';
import type {
  PlacementRow,
  ReplicaStepRow,
  ScalingFactRow,
  StatelessPanel,
} from '../../../domain/demo/scaling-stateless';

/**
 * ScalingStatelessDemo — the scaling topic's live state-placement panel
 * (demo block id `scaling:stateless`). One read where the server
 * introspects its own state placement: the process facts snapshot-read
 * off the composition root (pid, the live scenario flags, the posts
 * count), a two-replica round — replica A patches its scenario flags,
 * replica B (a world built exactly as a second process would build one)
 * never sees the write, while the same round against a REAL redis INCR
 * crosses effortlessly because the value lives in the store — and the
 * eleven-row inventory of every store this repo carries, each naming
 * where it lives and what a replica restart does to it.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: StatelessPanel };

function placementTone(row: PlacementRow): string {
  if (row.placement === 'in-process') return 'text-error';
  if (row.placement === 'externalized') return 'text-primary';
  return 'text-on-surface-variant';
}

function sideTone(row: ReplicaStepRow): string {
  if (row.side === 'shared') return 'text-primary';
  if (row.side === 'replica-b') return 'text-on-surface-variant';
  return 'text-on-surface';
}

function FactItem({ row }: { row: ScalingFactRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`scl-f-${row.id}`}>
      <span className="text-on-surface-variant">{row.label}:</span> {row.value}
    </p>
  );
}

function RoundStep({ row }: { row: ReplicaStepRow }) {
  return (
    <p className={`font-mono text-caption ${sideTone(row)}`} data-testid={`scl-r-${row.step}`}>
      {row.step}. [{row.side}] {row.label} — {row.observed}
    </p>
  );
}

function InventoryRowView({ row }: { row: PlacementRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`scl-i-${row.id}`}>
      <span className={placementTone(row)}>{row.placement}</span>{' '}
      <span className="text-on-surface-variant">({row.holder})</span> — {row.state}.{' '}
      <span className="text-on-surface-variant">restart: {row.restart}</span>
    </p>
  );
}

export default function ScalingStatelessDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetScalingStatelessDemoUseCase = container.getScalingStatelessDemoUseCase;
    const result: Result<StatelessPanel> = await useCase.panel();
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
    return <p data-testid="scl-loading">Walking one request through two replicas…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the statelessness panel"
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
    <section className="flex flex-col gap-sm" data-testid="scl-panel">
      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="scl-process"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">This process</span>{' '}
          <span className="text-on-surface-variant">
            snapshot-read off the composition root on this very request
          </span>
        </p>
        {data.process.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
      </section>

      <section className="flex flex-col gap-xxs" data-testid="scl-round">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The two-replica round</span>{' '}
          <span className="text-on-surface-variant">
            one logical request, two per-replica state worlds, one shared counter
          </span>
        </p>
        {data.replicaRound.map((row) => (
          <RoundStep key={row.step} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="scl-verdicts"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The verdicts</span>{' '}
          <span className="text-on-surface-variant">what the round proved, stated plainly</span>
        </p>
        {data.verdicts.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
      </section>

      <section className="flex flex-col gap-xxs" data-testid="scl-inventory">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">State-placement inventory</span>{' '}
          <span className="text-on-surface-variant">
            every store this repo carries — where it lives, what a replica restart does
          </span>
        </p>
        {data.inventory.map((row) => (
          <InventoryRowView key={row.id} row={row} />
        ))}
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="scl-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
