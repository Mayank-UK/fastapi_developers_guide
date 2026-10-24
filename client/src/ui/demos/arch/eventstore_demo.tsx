import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetArchEventStoreDemoUseCase } from '../../../domain/demo/get-arch-eventstore-demo-usecase';
import type {
  ArchEventStorePanel,
  ContrastRow,
} from '../../../domain/demo/arch-eventstore';

/**
 * ArchEventStoreDemo — the advanced-architecture topic's live
 * event-store panel (demo block id `arch:eventstore`). One read where
 * the server drove the REAL EventStore port end to end: five facts
 * appended with dense versions, the state folded back out one event at
 * a time, a second store instance proving replay determinism, and a
 * stale writer refused totally by the optimistic-concurrency check.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: ArchEventStorePanel };

function ContrastLine({ row }: { row: ContrastRow }) {
  return (
    <p
      className="font-mono text-caption text-on-surface"
      data-testid={`aes-c-${row.approach.split(' ')[0]}`}
    >
      <span className="text-primary">{row.approach}</span> — keeps: {row.keeps}.{' '}
      <span className="text-on-surface-variant">
        history: {row.history} · answers: {row.answers}
      </span>
    </p>
  );
}

export default function ArchEventStoreDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetArchEventStoreDemoUseCase = container.getArchEventStoreDemoUseCase;
    const result: Result<ArchEventStorePanel> = await useCase.eventstore();
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
    return <p data-testid="aes-loading">Appending facts and folding them back…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the event-store panel"
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
    <section className="flex flex-col gap-sm" data-testid="aes-panel">
      <section className="flex flex-col gap-xxs" data-testid="aes-appended">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">
            {data.store.stream} · {data.store.events} facts
          </span>{' '}
          <span className="text-on-surface-variant">
            appended through the {data.store.port} port ({data.store.adapter} adapter)
          </span>
        </p>
        {data.appended.map((event) => (
          <p
            key={event.eventId}
            className="font-mono text-caption text-on-surface"
            data-testid={`aes-v-${event.version}`}
          >
            v{event.version} <span className="text-primary">{event.eventType}</span>{' '}
            {event.payload}{' '}
            <span className="text-on-surface-variant">
              {event.eventId.slice(0, 8)}… at {event.occurredAt}
            </span>
          </p>
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="aes-fold"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The fold</span>{' '}
          <span className="text-on-surface-variant">
            state derived event by event — the same facts, the same answer, always
          </span>
        </p>
        {data.foldSteps.map((step) => (
          <p
            key={step.afterVersion}
            className="font-mono text-caption text-on-surface"
            data-testid={`aes-f-${step.afterVersion}`}
          >
            after v{step.afterVersion} <span className="text-primary">{step.eventType}</span>:{' '}
            {step.stateNow}
          </p>
        ))}
        <p className="font-mono text-caption text-on-surface" data-testid="aes-rebuild">
          rebuild in a second store:{' '}
          <span className={data.rebuild.matches ? 'text-primary' : 'text-error'}>
            matches={String(data.rebuild.matches)}
          </span>{' '}
          <span className="text-on-surface-variant">{data.rebuild.evidence}</span>
        </p>
      </section>

      <section className="flex flex-col gap-xxs" data-testid="aes-conflict">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The stale write, refused</span>{' '}
          <span className="text-on-surface-variant">
            optimistic concurrency: a lost race is told it lost
          </span>
        </p>
        <p className="font-mono text-caption text-on-surface" data-testid="aes-conflict-row">
          expected v{data.concurrency.expectedVersion} vs actual v
          {data.concurrency.actualVersion} →{' '}
          <span className="text-error">nothing stored</span> (log still{' '}
          {data.concurrency.storedEventsAfter} events)
        </p>
        <p className="text-caption text-on-surface-variant">{data.concurrency.evidence}</p>
      </section>

      <section className="flex flex-col gap-xxs" data-testid="aes-contrast">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Mutable row vs event stream</span>{' '}
          <span className="text-on-surface-variant">what each keeps, what each answers</span>
        </p>
        {data.contrast.map((row) => (
          <ContrastLine key={row.approach} row={row} />
        ))}
        <p className="font-mono text-caption text-on-surface" data-testid="aes-kinship">
          <span className="text-primary">{data.kinship.relative}</span> — same:{' '}
          {data.kinship.same}.{' '}
          <span className="text-on-surface-variant">different: {data.kinship.different}</span>
        </p>
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="aes-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
