import { useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  ArchHop,
  ArchRound,
  ArchStackLayer,
  ArchTracerData,
  HopEvidence,
  StackKind,
} from '../../../domain/demo/arch-tracer';

/**
 * ArchTracerDemo — the architecture topic's live tracer (demo block id
 * `arch:tracer`). Press the button and the payload answers with the
 * running app's own architecture: the introspected half (the built
 * middleware stack, the traced /api/posts route with its REAL dependency
 * tree, the composition wiring behind the port) and the measured half
 * (two REAL internal requests driven through the app at the ASGI
 * boundary — the ok round crossing every layer, the err round proving
 * the failure path end to end, timings only on the three boundary beats,
 * every hop labeled by how it is known).
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token), failures arrive as typed Failures inside Results, and the shared
 * ErrorPanel offers recovery.
 */

type TracerStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: ArchTracerData }
  | { state: 'error'; failure: Failure };

export function ArchTracerDemo() {
  const useCase = container.getArchTracerDemoUseCase;
  const [status, setStatus] = useState<TracerStatus>({ state: 'idle' });

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
      <section data-testid="at-form" className="flex items-center gap-sm">
        <button
          type="button"
          data-testid="at-run"
          onClick={fire}
          disabled={status.state === 'loading'}
          className="self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          Trace one request
        </button>
        {status.state === 'loading' && (
          <span data-testid="at-loading" className="text-caption text-on-surface-variant">
            driving the rounds…
          </span>
        )}
      </section>

      {status.state === 'error' && (
        <ErrorPanel subject="the architecture tracer" failure={status.failure} onRetry={fire} />
      )}

      {status.state === 'ready' && <TracerResult data={status.data} />}

      {status.state === 'idle' && (
        <p data-testid="at-idle" className="text-body-sm text-on-surface-variant">
          Trace one request and watch the map close: the stack this app
          really built, the route's real dependency tree, the wiring behind
          the port — and two internal requests crossing every layer, with
          the evidence labeled on every row.
        </p>
      )}
    </div>
  );
}

function TracerResult({ data }: { data: ArchTracerData }) {
  return (
    <section data-testid="at-result" className="flex flex-col gap-md">
      <div
        data-testid="at-wiring"
        className="flex flex-col gap-xxs rounded-md border border-outline bg-surface-tint px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          {data.wiring.adapter} implements {data.wiring.port} ·{' '}
          {data.wiring.useCases} wired by {data.wiring.wiredBy}
        </p>
        <p className="font-mono text-caption text-on-surface">
          {data.route.method} {data.route.template} → {data.route.endpoint} (
          response_model {data.route.responseModel})
        </p>
        <p className="text-caption text-on-surface-variant">
          {data.route.dependencies
            .map((dependency) => `${dependency.param} ← ${dependency.provider}`)
            .join(' · ')}{' '}
          — the endpoint's real dependency tree, introspected live.
        </p>
      </div>

      <div data-testid="at-stack" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          the live stack, outermost first (order 0 sees the request first):
        </p>
        {data.stack.map((layer) => (
          <StackRow key={`${layer.orderIndex}-${layer.name}`} layer={layer} />
        ))}
      </div>

      {data.rounds.map((round, index) => (
        <RoundCard key={`${index}-${round.requestLine}`} round={round} />
      ))}

      <p data-testid="at-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </section>
  );
}

function RoundCard({ round }: { round: ArchRound }) {
  return (
    <div
      data-testid={`at-round-${round.outcome}`}
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="flex flex-wrap items-baseline gap-xs font-mono text-caption text-on-surface">
        <span className={round.outcome === 'ok' ? 'text-primary' : 'text-secondary'}>
          {round.outcome.toUpperCase()}
        </span>
        <span>{round.requestLine}</span>
        <span className="text-on-surface-variant">→ {round.status}</span>
        <span className="text-on-surface-variant">
          {round.beats.map((beat) => `${beat.event}@${beat.offsetMs}ms`).join(' → ')}
        </span>
      </p>
      <p className="font-mono text-caption text-on-surface-variant">
        {round.facts.map((fact) => `${fact.name}: ${fact.value}`).join(' · ')}
      </p>
      {round.hops.map((hop, index) => (
        <HopRow key={`${index}-${hop.stage}`} hop={hop} />
      ))}
    </div>
  );
}

function StackRow({ layer }: { layer: ArchStackLayer }) {
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

function HopRow({ hop }: { hop: ArchHop }) {
  return (
    <p className="flex flex-wrap items-baseline gap-xs font-mono text-caption text-on-surface">
      <span className={evidenceClass(hop.evidence)}>{hop.evidence}</span>
      <span>{hop.stage}</span>
      <span className="text-on-surface-variant">{hop.layer}</span>
      <span className="font-sans text-caption text-on-surface-variant">{hop.detail}</span>
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

function evidenceClass(evidence: HopEvidence): string {
  if (evidence === 'measured') {
    return 'rounded-pill border border-primary px-sm py-xxs uppercase tracking-wide text-primary';
  }
  if (evidence === 'observed') {
    return 'rounded-pill border border-secondary px-sm py-xxs uppercase tracking-wide text-secondary';
  }
  return 'rounded-pill border border-outline px-sm py-xxs uppercase tracking-wide text-on-surface-variant';
}

export default ArchTracerDemo;
