import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetBestChecklistDemoUseCase } from '../../../domain/demo/get-best-checklist-demo-usecase';
import type {
  BestChecklistPanel,
  ChecklistItemRow,
  Verdict,
} from '../../../domain/demo/best-checklist';

/**
 * BestChecklistDemo — the best-practices topic's self-audit (demo block id
 * `best:checklist`). One live read of the server's audit: ten practice
 * areas of rows, every verdict computed at request time — 'live' rows from
 * real probes through the app, 'file' rows from real repo reads, 'manual'
 * rows claiming nothing and saying why. The anti-checklist of deliberate
 * not-does rides along, and the score line counts pass/fail/manual
 * without spinning. Read-only by design: a self-audit that could be
 * edited would not be one.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: BestChecklistPanel };

const VERDICT_TONE: Record<Verdict, string> = {
  pass: 'border-primary text-primary',
  fail: 'border-error text-error',
  manual: 'border-warning text-warning',
};

function VerdictBadge({ row }: { row: ChecklistItemRow }) {
  return (
    <span
      data-testid={`bc-verdict-${row.id}`}
      className={`rounded-sm border px-xxs font-mono text-caption ${VERDICT_TONE[row.verdict]}`}
    >
      {row.verdict}
    </span>
  );
}

function ItemLine({ row }: { row: ChecklistItemRow }) {
  return (
    <div
      data-testid={`bc-item-${row.id}`}
      className="flex flex-col gap-xxs border-l border-outline pl-sm"
    >
      <div className="flex flex-wrap items-baseline gap-x-xs gap-y-xxs">
        <VerdictBadge row={row} />
        <span className="text-caption text-on-surface">{row.practice}</span>
        <span className="font-mono text-outline">[{row.checkKind}]</span>
      </div>
      {row.evidence.length > 0 && (
        <ul className="flex flex-col gap-xxs" data-testid={`bc-evidence-${row.id}`}>
          {row.evidence.map((line) => (
            <li key={line} className="font-mono text-caption text-on-surface-variant">
              {line}
            </li>
          ))}
        </ul>
      )}
      {row.whyManual !== null && (
        <p className="text-caption text-warning" data-testid={`bc-why-${row.id}`}>
          why manual: {row.whyManual}
        </p>
      )}
    </div>
  );
}

export default function BestChecklistDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetBestChecklistDemoUseCase = container.getBestChecklistDemoUseCase;
    const result: Result<BestChecklistPanel> = await useCase.panel();
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
    return <p data-testid="bc-loading">Running the live self-audit…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the self-audit panel"
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
    <section className="flex flex-col gap-sm" data-testid="bc-panel">
      <header className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs">
        <p className="font-mono text-caption text-primary" data-testid="bc-summary">
          {data.summary.passed} passed · {data.summary.failed} failed ·{' '}
          {data.summary.manual} manual — of {data.summary.items} checks
        </p>
        <p className="text-caption text-on-surface-variant" data-testid="bc-areas-count">
          {data.areas.length} practice areas
        </p>
      </header>

      {data.areas.map((area) => (
        <section
          key={area.id}
          className="flex flex-col gap-xxs"
          data-testid={`bc-area-${area.id}`}
        >
          <div className="flex flex-wrap items-baseline gap-x-xs gap-y-xxs">
            <h4 className="text-body font-medium text-on-surface">{area.title}</h4>
            <span className="text-caption text-on-surface-variant">{area.note}</span>
          </div>
          {area.items.map((row) => (
            <ItemLine key={row.id} row={row} />
          ))}
        </section>
      ))}

      <section className="flex flex-col gap-xxs" data-testid="bc-not-dones">
        <h4 className="text-body font-medium text-warning">The anti-checklist</h4>
        {data.notDones.map((row) => (
          <div
            key={row.id}
            className="flex flex-col gap-xxs border-l border-warning pl-sm"
            data-testid={`bc-not-done-${row.id}`}
          >
            <span className="text-caption text-on-surface">{row.notDone}</span>
            <span className="text-caption text-on-surface-variant">{row.reason}</span>
            {row.artifacts.map((artifact) => (
              <span key={artifact} className="font-mono text-caption text-outline">
                {artifact}
              </span>
            ))}
          </div>
        ))}
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="bc-honesty">
        {data.honestyNote}
      </p>
    </section>
  );
}
