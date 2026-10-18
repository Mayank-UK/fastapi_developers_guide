import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { GetRuntimeAsyncDemoUseCase } from '../../../domain/demo/get-runtime-async-demo-usecase';
import type {
  RuntimeAsyncDemoData,
  TimingRun,
} from '../../../domain/demo/runtime-async';

/**
 * RuntimeAsyncDemo — the python-runtime topic's timing demo (demo block id
 * `runtime:async`). It renders the payload of GET /api/demo/runtime/async,
 * which the server MEASURES on every request: the same three simulated-I/O
 * coroutines awaited one after another (cost: the sum) versus run under
 * asyncio.gather (cost: the longest), per-task timings, the two runs'
 * completion orders, the speedup ratio, and the two-actor trace that
 * proves await yields control step by step.
 *
 * Dependency flow mirrors the views: the hook resolves the use case from
 * the container (its default parameter is the spec seam — tests substitute
 * fakes through the container token instead), failures arrive as typed
 * Failures inside Results, and `retry` re-runs the measurement.
 */

type RuntimeAsyncDemoStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: RuntimeAsyncDemoData }
  | { state: 'error'; failure: Failure };

export function useRuntimeAsyncDemo(
  useCase: GetRuntimeAsyncDemoUseCase = container.getRuntimeAsyncDemoUseCase,
): { status: RuntimeAsyncDemoStatus; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<RuntimeAsyncDemoStatus>({ state: 'idle' });

  useEffect(() => {
    let cancelled = false;
    setStatus({ state: 'loading' });

    void useCase.execute().then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setStatus({ state: 'ready', data: result.value });
      } else {
        setStatus({ state: 'error', failure: result.failure });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [useCase, attempt]);

  const retry = () => setAttempt((current) => current + 1);
  return { status, retry };
}

export function RuntimeAsyncDemo() {
  const { status, retry } = useRuntimeAsyncDemo();

  if (status.state === 'idle' || status.state === 'loading') {
    return (
      <p data-testid="runtime-async-loading" className="text-body-sm text-on-surface-variant">
        measuring the event loop…
      </p>
    );
  }

  if (status.state === 'error') {
    return <ErrorPanel subject="the async-timing demo" failure={status.failure} onRetry={retry} />;
  }

  const { sequential, gathered, speedup, trace } = status.data;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="ra-speedup"
        className="flex flex-col gap-xs rounded-md border border-outline bg-surface-tint px-md py-sm"
      >
        <h4 className="font-display text-title-sm text-on-surface">Sum vs longest</h4>
        <p className="font-mono text-body-sm">
          <span data-testid="ra-sequential-ms" className="text-on-surface">
            {sequential.elapsedMs.toFixed(1)} ms
          </span>
          <span className="text-on-surface-variant"> sequential → </span>
          <span data-testid="ra-gathered-ms" className="text-secondary">
            {gathered.elapsedMs.toFixed(1)} ms
          </span>
          <span className="text-on-surface-variant"> gathered</span>
        </p>
        <p className="text-body-sm text-on-surface-variant">
          speedup <span data-testid="ra-speedup-value" className="font-mono text-secondary">{speedup.toFixed(2)}×</span>{' '}
          — three overlapping waits, measured on this request.
        </p>
      </section>

      <section data-testid="ra-runs" className="grid gap-sm md:grid-cols-2">
        <RunPanel testId="ra-sequential" run={sequential} heading="Sequential — the sum" />
        <RunPanel testId="ra-gathered" run={gathered} heading="Gathered — the longest" />
      </section>

      <section data-testid="ra-trace" className="flex flex-col gap-sm">
        <h4 className="font-display text-title-sm text-on-surface">
          The trace: await yields control
        </h4>
        <div className="flex flex-wrap gap-xxs" data-testid="ra-trace-events">
          {trace.map((event, index) => (
            <span
              key={`${event.actor}-${event.event}-${String(index)}`}
              className={
                event.actor === 'alpha'
                  ? 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface'
                  : 'rounded-pill border border-outline bg-surface-tint px-sm py-xxs font-mono text-caption text-secondary'
              }
            >
              {event.actor}:{event.event}
            </span>
          ))}
        </div>
        <p className="text-body-sm text-on-surface-variant">
          Two actors, one event per step, separated only by{' '}
          <code className="font-mono">asyncio.sleep(0)</code> — the loop's ready
          queue is first-in-first-out, so they alternate.
        </p>
      </section>
    </div>
  );
}

function RunPanel({
  testId,
  heading,
  run,
}: {
  testId: string;
  heading: string;
  run: TimingRun;
}) {
  return (
    <div data-testid={testId} className="flex flex-col gap-xxs rounded-md border border-outline px-md py-sm">
      <h5 className="font-display text-title-sm text-on-surface">{heading}</h5>
      <p className="font-mono text-caption text-on-surface-variant">
        finished: {run.completionOrder.join(' → ')}
      </p>
      <div className="overflow-x-auto rounded-md border border-outline">
        <table className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">task</th>
              <th scope="col" className="px-sm py-xxs">simulated</th>
              <th scope="col" className="px-sm py-xxs">measured</th>
            </tr>
          </thead>
          <tbody>
            {run.perTask.map((task) => (
              <tr key={task.name} className="border-t border-outline">
                <td className="px-sm py-xxs text-on-surface">{task.name}</td>
                <td className="px-sm py-xxs text-on-surface-variant">{task.simulatedIoMs} ms</td>
                <td className="px-sm py-xxs text-secondary">{task.measuredMs.toFixed(1)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RuntimeAsyncDemo;
