import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  OutboxConsumeOutcome,
  OutboxPanel,
  OutboxWriteOutcome,
  RelayOutcome,
} from '../../../domain/demo/msg-outbox';

/**
 * OutboxDemo — the messaging topic's outbox lab (demo block id
 * `msg:outbox`). One panel bridging PostgreSQL and Redis for real: the
 * roster shows the outbox table's counts, its recent rows with published
 * stamps, the relay's stream, and the demo's counters; the buttons run
 * the one-transaction create (post + event, both or neither), the relay
 * cycle (optionally dying between publish and mark), and the idempotent
 * consume whose counts prove the exactly-once effect.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: OutboxPanel };

type WriteStatus =
  | { state: 'idle' }
  | { state: 'failed'; failure: Failure }
  | { state: 'done'; row: OutboxWriteOutcome };

type RelayStatus =
  | { state: 'idle' }
  | { state: 'failed'; failure: Failure }
  | { state: 'done'; row: RelayOutcome };

export function OutboxDemo() {
  const useCase = container.getMsgOutboxDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [write, setWrite] = useState<WriteStatus>({ state: 'idle' });
  const [relay, setRelay] = useState<RelayStatus>({ state: 'idle' });
  const [consume, setConsume] = useState<OutboxConsumeOutcome | null>(null);
  const [title, setTitle] = useState('A post born with its event');
  const [actionFailed, setActionFailed] = useState<Failure | null>(null);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      setPanel(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  /** Run one action, then refresh the roster so counts stay honest. */
  function runAction<T>(action: () => Promise<Result<T>>, onDone: (value: T) => void): void {
    setActionFailed(null);
    void action().then((result) => {
      if (result.ok) {
        onDone(result.value);
        refreshPanel();
      } else {
        setActionFailed(result.failure);
      }
    });
  }

  const create = () =>
    runAction(() => useCase.create(title, 'both rows or neither'), (row) =>
      setWrite({ state: 'done', row }),
    );

  if (panel.state === 'loading') {
    return (
      <p data-testid="msg-outbox-loading" className="text-body-sm text-on-surface-variant">
        reading the outbox state…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the outbox lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="msg-outbox-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          {data.table} → {data.stream}
        </p>
        <p data-testid="msg-outbox-stats" className="font-mono text-caption text-on-surface">
          total {data.stats.total} · published {data.stats.published} · unpublished{' '}
          {data.stats.unpublished}
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          telemetry: creates {data.telemetry.creates} · cycles {data.telemetry.relayCycles} ·
          crashes {data.telemetry.crashSimulations} · processed {data.telemetry.eventsProcessed} ·
          dupes skipped {data.telemetry.duplicatesSkipped}
        </p>
        {data.outbox.slice(-3).map((row) => (
          <p key={row.eventId} className="font-mono text-caption text-on-surface-variant">
            {row.aggregate} · {row.publishedAt ? `published ${row.publishedAt}` : 'unpublished'}
          </p>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <input
          type="text"
          value={title}
          maxLength={120}
          onChange={(event) => setTitle(event.target.value)}
          aria-label="post title"
          className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
        />
        <button
          type="button"
          onClick={create}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          create post + event (one tx)
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.relay(false), (row) => setRelay({ state: 'done', row }))}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          relay cycle
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.relay(true), (row) => setRelay({ state: 'done', row }))}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          relay + crash window
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.consume(), setConsume)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          consume (dedupe)
        </button>
      </div>

      {actionFailed && (
        <p data-testid="msg-outbox-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {write.state === 'done' && (
        <section
          data-testid="msg-outbox-write"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            {write.row.committed ? 'committed — both halves' : 'rolled back — neither half'}
          </p>
          {write.row.post && (
            <p className="font-mono text-caption text-on-surface">
              post {write.row.post.id} · {write.row.post.slug} · {write.row.post.author}
            </p>
          )}
          {write.row.event && (
            <p className="font-mono text-caption text-on-surface">
              event {write.row.event.eventId} · {write.row.event.aggregate}
            </p>
          )}
          <p className="text-caption text-on-surface-variant">{write.row.detail}</p>
        </section>
      )}

      {relay.state === 'done' && (
        <section
          data-testid="msg-outbox-relay"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            cycle {relay.row.cycle} · discovered {relay.row.discovered} · published{' '}
            {relay.row.published.length} · marked {relay.row.marked}
            {relay.row.crashed ? ' · CRASHED before marking' : ''}
          </p>
          <p className="text-caption text-on-surface-variant">{relay.row.detail}</p>
        </section>
      )}

      {consume && (
        <section
          data-testid="msg-outbox-consume"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            {consume.entries} entries → processed {consume.processed} · skipped{' '}
            {consume.skippedDuplicates}
          </p>
          <p className="text-caption text-on-surface-variant">{consume.proof}</p>
        </section>
      )}

      <p data-testid="msg-outbox-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default OutboxDemo;
