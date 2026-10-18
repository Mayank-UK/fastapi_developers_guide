import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  ConsumeOutcome,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamPanel,
} from '../../../domain/demo/msg-stream';

/**
 * StreamDemo — the messaging topic's stream lab (demo block id
 * `msg:stream`). One panel over the real Redis Stream: the roster shows
 * the log in id order with its length, last id, and pending count;
 * buttons produce a note (XADD), consume as the healthy worker (read
 * then ack) or the poison worker (read, never ack — the backlog grows),
 * list the pending entries with their owner and delivery counts, and
 * reclaim the stale ones with XAUTOCLAIM.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: StreamPanel };

type ActionOutcome =
  | { state: 'idle' }
  | { state: 'failed'; failure: Failure }
  | { state: 'done'; label: string; detail: string };

export function StreamDemo() {
  const useCase = container.getMsgStreamDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [outcome, setOutcome] = useState<ActionOutcome>({ state: 'idle' });
  const [pending, setPending] = useState<PendingListOutcome | null>(null);
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

  const produce = () =>
    runAction(() => useCase.produce('hello from the panel'), (row: ProduceOutcome) =>
      setOutcome({
        state: 'done',
        label: `produce → ${row.entryId}`,
        detail: row.detail,
      }),
    );

  const consumeHealthy = () =>
    runAction(() => useCase.consume('healthy'), (row: ConsumeOutcome) =>
      setOutcome({
        state: 'done',
        label: `healthy read → delivered ${row.delivered.length}, acked ${row.acked}`,
        detail: row.detail,
      }),
    );

  const consumePoison = () =>
    runAction(() => useCase.consume('poison'), (row: ConsumeOutcome) =>
      setOutcome({
        state: 'done',
        label: `poison read → delivered ${row.delivered.length}, acked ${row.acked}`,
        detail: row.detail,
      }),
    );

  const readPending = () =>
    runAction(() => useCase.pending(), (row: PendingListOutcome) => setPending(row));

  const reclaim = () =>
    runAction(() => useCase.reclaim(0), (row: ReclaimOutcome) =>
      setOutcome({
        state: 'done',
        label: `reclaim → claimed ${row.claimed.length}, acked ${row.acked}`,
        detail: row.detail,
      }),
    );

  if (panel.state === 'loading') {
    return (
      <p data-testid="msg-stream-loading" className="text-body-sm text-on-surface-variant">
        reading the stream state…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the stream lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="msg-stream-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          stream · {data.stream} · group {data.group}
        </p>
        <p data-testid="msg-stream-facts" className="font-mono text-caption text-on-surface">
          length {data.length} · last {data.lastId ?? '—'} · pending {data.pendingCount}
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          {data.entries.slice(-5).map((entry) => `${entry.id} ${entry.payload}`).join(' · ') ||
            '(empty log)'}
        </p>
        <p className="text-caption text-on-surface-variant">
          {data.healthyConsumer} acks its work · {data.poisonConsumer} never does
        </p>
      </section>

      <div className="flex flex-wrap gap-xs">
        <button
          type="button"
          onClick={produce}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          produce (XADD)
        </button>
        <button
          type="button"
          onClick={consumeHealthy}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          consume healthy → ack
        </button>
        <button
          type="button"
          onClick={consumePoison}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          consume poison → no ack
        </button>
        <button
          type="button"
          onClick={readPending}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          pending list
        </button>
        <button
          type="button"
          onClick={reclaim}
          className="rounded-md border border-outline px-sm py-xxs font-mono text-caption hover:border-primary hover:text-primary"
        >
          reclaim (XAUTOCLAIM)
        </button>
      </div>

      {actionFailed && (
        <p data-testid="msg-stream-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {outcome.state === 'done' && (
        <section
          data-testid="msg-stream-outcome"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">{outcome.label}</p>
          <p className="text-caption text-on-surface-variant">{outcome.detail}</p>
        </section>
      )}

      {pending && (
        <section
          data-testid="msg-stream-pending"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            pending entries list · {pending.entries.length}
          </p>
          {pending.entries.map((entry) => (
            <p key={entry.entryId} className="font-mono text-caption text-on-surface">
              {entry.entryId} · {entry.consumer} · idle {entry.idleMs}ms · deliveries{' '}
              {entry.deliveries}
            </p>
          ))}
          <p className="text-caption text-on-surface-variant">{pending.detail}</p>
        </section>
      )}

      <p data-testid="msg-stream-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default StreamDemo;
