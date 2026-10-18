import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  DepLifecycleEvent,
  DepLifecycleLogData,
  DepLifecycleSpanData,
} from '../../../domain/demo/dep-lifecycle';

/**
 * DepLifecycleDemo — the dependency topic's yield-dependency demo (demo
 * block id `dep:lifecycle`). Fire one wrapped request and the server
 * answers with what the handler could know — span id, setup timestamp,
 * how far in the handler ran, and pendingEvents confessing the teardown
 * that had not run when those bytes were built. The timeline below is the
 * shared span log: the same request's four beats, sequenced
 * setup → handler → response → teardown, the teardown AFTER the response —
 * FastAPI closes the request's dependency stack only after the bytes are
 * sent, and this log is where that fact shows up as data.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token — the documented replace-a-singleton seam); failures arrive as
 * typed Failures inside Results and render through the shared ErrorPanel.
 */

type SpanStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: DepLifecycleSpanData }
  | { state: 'error'; failure: Failure };

type LogStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: DepLifecycleLogData }
  | { state: 'error'; failure: Failure };

const EVENT_BADGE_CLASS: Record<DepLifecycleEvent['event'], string> = {
  setup: 'text-secondary',
  handler: 'text-on-surface',
  response: 'text-primary',
  teardown: 'text-error',
};

const buttonClass =
  'rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide ' +
  'text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

export function DepLifecycleDemo() {
  const useCase = container.getDepLifecycleDemoUseCase;
  const [span, setSpan] = useState<SpanStatus>({ state: 'idle' });
  const [log, setLog] = useState<LogStatus>({ state: 'loading' });

  const refreshLog = useCallback(() => {
    setLog({ state: 'loading' });
    void useCase.log().then((result) => {
      setLog(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    refreshLog();
  }, [refreshLog]);

  const fire = () => {
    setSpan({ state: 'loading' });
    void useCase.fire().then((result) => {
      setSpan(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
      // The teardown landed after the response left; the log now holds it.
      refreshLog();
    });
  };

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="dep-lifecycle-controls" className="flex flex-wrap items-center gap-sm">
        <button
          type="button"
          data-testid="dep-lifecycle-fire"
          onClick={fire}
          disabled={span.state === 'loading'}
          className={buttonClass}
        >
          Fire a wrapped request
        </button>
        <button
          type="button"
          data-testid="dep-lifecycle-refresh"
          onClick={refreshLog}
          disabled={log.state === 'loading'}
          className={buttonClass}
        >
          Refresh log
        </button>
        {(span.state === 'loading' || log.state === 'loading') && (
          <span data-testid="dep-lifecycle-loading" className="text-caption text-on-surface-variant">
            resolving…
          </span>
        )}
      </section>

      {span.state === 'error' && (
        <ErrorPanel subject="the lifecycle request" failure={span.failure} onRetry={fire} />
      )}
      {span.state === 'ready' && <SpanFacts data={span.data} />}
      {span.state === 'idle' && (
        <p data-testid="dep-lifecycle-idle" className="text-body-sm text-on-surface-variant">
          Fire a request to open a span — the response can only report what
          had already happened; the log below holds the rest.
        </p>
      )}

      {log.state === 'error' && (
        <ErrorPanel subject="the span log" failure={log.failure} onRetry={refreshLog} />
      )}
      {log.state === 'ready' && <SpanTimeline data={log.data} />}
    </div>
  );
}

function SpanFacts({ data }: { data: DepLifecycleSpanData }) {
  return (
    <div
      data-testid="dep-lifecycle-span"
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="text-caption text-on-surface">
        span <span className="font-mono text-secondary">{data.spanId}</span> — setup at{' '}
        <span className="font-mono">{data.setupAt}</span>, handler ran {data.handlerOffsetMs} ms
        in.
      </p>
      <p data-testid="dep-lifecycle-pending" className="text-caption text-on-surface-variant">
        pendingEvents: <span className="font-mono text-error">[{data.pendingEvents.join(', ')}]</span>{' '}
        — the teardown had not run when this body was built; it runs after the bytes are sent.
      </p>
    </div>
  );
}

function SpanTimeline({ data }: { data: DepLifecycleLogData }) {
  const ordered = [...data.events].sort((a, b) => b.sequence - a.sequence);
  return (
    <section data-testid="dep-lifecycle-log" className="flex flex-col gap-xs">
      <p className="text-caption text-on-surface-variant">
        the shared span log — last {data.capacity} events, newest first;{' '}
        <span className="text-error">teardown</span> sequenced after{' '}
        <span className="text-primary">response</span>
      </p>
      <div className="overflow-x-auto rounded-md border border-outline">
        <table data-testid="dep-lifecycle-table" className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">seq</th>
              <th scope="col" className="px-sm py-xxs">span</th>
              <th scope="col" className="px-sm py-xxs">event</th>
              <th scope="col" className="px-sm py-xxs">offset</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((event) => (
              <tr key={event.sequence} data-testid={`dep-lifecycle-row-${event.sequence}`} className="border-t border-outline">
                <td className="px-sm py-xxs text-on-surface-variant">{event.sequence}</td>
                <td className="px-sm py-xxs text-on-surface-variant">{event.spanId}</td>
                <td className={`px-sm py-xxs ${EVENT_BADGE_CLASS[event.event]}`}>
                  {event.event}
                </td>
                <td className="px-sm py-xxs text-on-surface-variant">+{event.offsetMs} ms</td>
              </tr>
            ))}
            {ordered.length === 0 && (
              <tr>
                <td colSpan={4} data-testid="dep-lifecycle-empty" className="px-sm py-xs text-on-surface-variant">
                  the ring is empty — fire a request
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default DepLifecycleDemo;
