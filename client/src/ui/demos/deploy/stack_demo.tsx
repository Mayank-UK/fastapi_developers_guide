import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetDeployStackDemoUseCase } from '../../../domain/demo/get-deploy-stack-demo-usecase';
import type { DeployStackPanel, StackItemRow } from '../../../domain/demo/deploy-stack';

/**
 * DeployStackDemo — the deployment topic's deploy-stack inspection (demo
 * block id `deploy:stack`). One live read where the server walks its own
 * deploy surface: the runtime block carries facts THIS process always
 * has (env, interpreter, pid, the server command line, a REAL internal
 * /api/health), and each area rows over one slice of the surface —
 * platform, app stack, edge, images, pipeline, release, parity,
 * kubernetes. The read that matters: every pass row carries the evidence
 * that produced it, and manual rows say exactly why the check cannot run
 * from where the server stands (the live container's bind mount is
 * server/ only) — never a faked pass.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: DeployStackPanel };

function verdictTone(row: StackItemRow): string {
  if (row.verdict === 'pass') return 'text-primary';
  if (row.verdict === 'fail') return 'text-error';
  return 'text-on-surface-variant';
}

function Item({ row }: { row: StackItemRow }) {
  return (
    <section
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      data-testid={`dsk-item-${row.id}`}
    >
      <p className="text-caption text-on-surface">
        <span className={`font-mono ${verdictTone(row)}`}>{row.verdict}</span>{' '}
        <span className="text-on-surface-variant">[{row.checkKind}]</span> {row.claim}
      </p>
      {row.evidence.map((line) => (
        <p key={line} className="font-mono text-caption text-on-surface-variant">
          {line}
        </p>
      ))}
      {row.whyManual && (
        <p className="text-caption text-on-surface-variant" data-testid={`dsk-why-${row.id}`}>
          {row.whyManual}
        </p>
      )}
    </section>
  );
}

export default function DeployStackDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetDeployStackDemoUseCase = container.getDeployStackDemoUseCase;
    const result: Result<DeployStackPanel> = await useCase.panel();
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
    return <p data-testid="dsk-loading">Inspecting the deploy surface…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the deploy-stack inspection"
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
    <section className="flex flex-col gap-sm" data-testid="dsk-panel">
      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="dsk-runtime"
      >
        {data.runtime.map((row) => (
          <p key={row.id} className="font-mono text-caption text-on-surface">
            <span className="text-on-surface-variant">{row.label}:</span> {row.value}
          </p>
        ))}
      </section>

      {data.areas.map((area) => (
        <section key={area.id} className="flex flex-col gap-xxs" data-testid={`dsk-area-${area.id}`}>
          <p className="text-caption text-on-surface">
            <span className="font-mono text-primary">{area.title}</span>{' '}
            <span className="text-on-surface-variant">{area.note}</span>
          </p>
          {area.items.map((row) => (
            <Item key={row.id} row={row} />
          ))}
        </section>
      ))}

      <p className="text-caption text-on-surface-variant" data-testid="dsk-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
