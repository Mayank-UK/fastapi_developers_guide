import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { GetRuntimeStreamingDemoUseCase } from '../../../domain/demo/get-runtime-streaming-demo-usecase';
import type { StreamChunk } from '../../../domain/demo/runtime-streaming';

/**
 * RuntimeStreamingDemo — the python-runtime topic's streaming demo (demo
 * block id `runtime:streaming`). It consumes GET /api/demo/runtime/streaming
 * — a real async generator served as NDJSON — and renders each line as it
 * arrives: an open line, six items each preceded by an awaited tick, and a
 * closing line with the measured cost of the whole stream. When the
 * browser's stream seam is available the list visibly grows as the wire
 * delivers; otherwise the collected result renders at once (same producer,
 * same lines). Failures degrade to the shared error panel with recovery.
 */

type RuntimeStreamingDemoStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'streaming'; chunks: StreamChunk[] }
  | { state: 'complete'; chunks: StreamChunk[] }
  | { state: 'error'; failure: Failure };

export function useRuntimeStreamingDemo(
  useCase: GetRuntimeStreamingDemoUseCase = container.getRuntimeStreamingDemoUseCase,
): { status: RuntimeStreamingDemoStatus; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<RuntimeStreamingDemoStatus>({ state: 'idle' });

  useEffect(() => {
    let cancelled = false;
    setStatus({ state: 'loading' });

    void useCase.execute((chunk) => {
      if (cancelled) return;
      setStatus((current) => ({
        state: 'streaming',
        chunks: [...('chunks' in current ? current.chunks : []), chunk],
      }));
    }).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setStatus({ state: 'complete', chunks: result.value.chunks });
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

export function RuntimeStreamingDemo() {
  const { status, retry } = useRuntimeStreamingDemo();

  if (status.state === 'idle' || status.state === 'loading') {
    return (
      <p data-testid="runtime-streaming-loading" className="text-body-sm text-on-surface-variant">
        opening the stream…
      </p>
    );
  }

  if (status.state === 'error') {
    return (
      <ErrorPanel subject="the streaming demo" failure={status.failure} onRetry={retry} />
    );
  }

  const { chunks } = status;
  const closed = chunks.length > 0 ? chunks[chunks.length - 1] : undefined;
  const isComplete = status.state === 'complete';

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="rs-status"
        className="flex flex-col gap-xs rounded-md border border-outline bg-surface-tint px-md py-sm"
      >
        <h4 className="font-display text-title-sm text-on-surface">
          {isComplete ? 'Stream complete' : 'Receiving…'}
        </h4>
        <p className="font-mono text-body-sm text-on-surface">
          <span data-testid="rs-line-count">{chunks.length}</span>
          <span className="text-on-surface-variant"> lines · application/x-ndjson</span>
        </p>
        {closed !== undefined && closed.kind === 'closed' && (
          <p data-testid="rs-closed" className="font-mono text-caption text-on-surface-variant">
            {closed.itemsDelivered} items delivered in{' '}
            <span className="text-secondary">{closed.totalMs} ms</span> (measured)
          </p>
        )}
      </section>

      <section data-testid="rs-lines" className="flex flex-col gap-xxs">
        {chunks.map((chunk) => (
          <p
            key={`${String(chunk.seq)}-${chunk.label}`}
            data-testid={`rs-line-${chunk.seq}`}
            className="rounded-md border border-outline px-sm py-xxs font-mono text-caption text-on-surface"
          >
            <span className="text-on-surface-variant">{String(chunk.seq).padStart(2, '0')} </span>
            <span className={chunk.kind === 'closed' ? 'text-secondary' : 'text-on-surface'}>
              {chunk.label}
            </span>
            {chunk.detail !== undefined && (
              <span className="text-on-surface-variant"> — {chunk.detail}</span>
            )}
          </p>
        ))}
      </section>
    </div>
  );
}

export default RuntimeStreamingDemo;
