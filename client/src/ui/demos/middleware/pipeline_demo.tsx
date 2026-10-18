import { useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  MiddlewarePipelineData,
  StackKind,
  TracePhase,
} from '../../../domain/demo/middleware-pipeline';

/**
 * MiddlewarePipelineDemo — the middleware topic's live onion (demo block id
 * `middleware:pipeline`). Press the button and one real request walks the
 * running middleware chain: the payload reports the stack the app actually
 * built (outermost first, classified framework / user / router), replays
 * exactly that composition as a pure-ASGI trace — request events descend,
 * the handler runs once in the middle, response events unwind in reverse —
 * and carries the request id the real RequestIdMiddleware assigned to the
 * request you just made (the same value echoed on the response's
 * x-request-id header).
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token), failures arrive as typed Failures inside Results, and the shared
 * ErrorPanel offers recovery.
 */

type PipelineStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: MiddlewarePipelineData }
  | { state: 'error'; failure: Failure };

export function MiddlewarePipelineDemo() {
  const useCase = container.getMiddlewarePipelineDemoUseCase;
  const [status, setStatus] = useState<PipelineStatus>({ state: 'idle' });

  const fire = () => {
    setStatus({ state: 'loading' });
    void useCase.execute().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  };

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="mp-form" className="flex items-center gap-sm">
        <button
          type="button"
          data-testid="mp-run"
          onClick={fire}
          disabled={status.state === 'loading'}
          className="self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send one request
        </button>
        {status.state === 'loading' && (
          <span data-testid="mp-loading" className="text-caption text-on-surface-variant">
            descending the stack…
          </span>
        )}
      </section>

      {status.state === 'error' && (
        <ErrorPanel subject="the middleware pipeline" failure={status.failure} onRetry={fire} />
      )}

      {status.state === 'ready' && <PipelineResult data={status.data} />}

      {status.state === 'idle' && (
        <p data-testid="mp-idle" className="text-body-sm text-on-surface-variant">
          Send one request and watch the onion: the stack this app really
          built, a traced run proving the wrap order, and the request id
          the real middleware assigned to the click you just made.
        </p>
      )}
    </div>
  );
}

function PipelineResult({ data }: { data: MiddlewarePipelineData }) {
  return (
    <section data-testid="mp-result" className="flex flex-col gap-md">
      <div
        data-testid="mp-request-id"
        className="flex flex-col gap-xxs rounded-md border border-outline bg-surface-tint px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          {data.requestIdHeader}: <span className="text-primary">{data.requestId}</span>
        </p>
        <p className="text-caption text-on-surface-variant">
          assigned request-side by the real RequestIdMiddleware — the same value
          is stamped on the response header carrying this payload.
        </p>
      </div>

      <div data-testid="mp-stack" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          the live stack, outermost first (order 0 sees the request first):
        </p>
        {data.stack.map((layer) => (
          <StackRow key={`${layer.orderIndex}-${layer.name}`} layer={layer} />
        ))}
      </div>

      <div data-testid="mp-orders" className="flex flex-wrap gap-md">
        <OrderColumn label="request side ↓" names={data.requestSideOrder} emphasize />
        <OrderColumn label="response side ↑" names={data.responseSideOrder} />
      </div>

      <div data-testid="mp-trace" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          one request, traced (sequence numbers are the chronological truth):
        </p>
        {data.trace.map((event) => (
          <TraceRow key={event.sequence} event={event} />
        ))}
      </div>

      <p data-testid="mp-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </section>
  );
}

function StackRow({ layer }: { layer: { name: string; kind: StackKind; orderIndex: number; role: string } }) {
  return (
    <p className="flex flex-wrap items-baseline gap-xs font-mono text-caption text-on-surface">
      <span className="rounded-pill border border-outline px-sm py-xxs text-on-surface-variant">
        {layer.orderIndex}
      </span>
      <span className={kindClass(layer.kind)}>{layer.name}</span>
      <span className="font-sans text-caption uppercase tracking-wide text-on-surface-variant">
        {layer.kind}
      </span>
      <span className="font-sans text-caption text-on-surface-variant">{layer.role}</span>
    </p>
  );
}

function OrderColumn({
  label,
  names,
  emphasize = false,
}: {
  label: string;
  names: string[];
  emphasize?: boolean;
}) {
  return (
    <div className="flex flex-col gap-xxs">
      <p className="text-caption text-on-surface-variant">{label}</p>
      {names.map((name, index) => (
        <p key={`${index}-${name}`} className="font-mono text-caption text-on-surface">
          {emphasize && index === 0 ? <span className="text-primary">{name}</span> : name}
        </p>
      ))}
    </div>
  );
}

function TraceRow({
  event,
}: {
  event: { stage: string; phase: TracePhase; sequence: number; note: string };
}) {
  return (
    <p className="flex flex-wrap items-baseline gap-xs font-mono text-caption text-on-surface">
      <span className="text-on-surface-variant">{event.sequence}</span>
      <span className={phaseClass(event.phase)}>{event.phase}</span>
      <span>{event.stage}</span>
      <span className="font-sans text-caption text-on-surface-variant">{event.note}</span>
    </p>
  );
}

function kindClass(kind: StackKind): string {
  if (kind === 'user') {
    return 'rounded-pill border border-primary px-sm py-xxs text-primary';
  }
  if (kind === 'router') {
    return 'rounded-pill border border-secondary px-sm py-xxs text-secondary';
  }
  return 'rounded-pill border border-outline px-sm py-xxs text-on-surface-variant';
}

function phaseClass(phase: TracePhase): string {
  if (phase === 'request') {
    return 'rounded-pill border border-primary px-sm py-xxs uppercase tracking-wide text-primary';
  }
  if (phase === 'handler') {
    return 'rounded-pill border border-secondary px-sm py-xxs uppercase tracking-wide text-secondary';
  }
  return 'rounded-pill border border-outline px-sm py-xxs uppercase tracking-wide text-on-surface-variant';
}

export default MiddlewarePipelineDemo;
