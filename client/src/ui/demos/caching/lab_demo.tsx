import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  CachingLabDemo as CachingLabModel,
  ConditionalRound,
  InvalidationOutcome,
  StampedeOutcome,
} from '../../../domain/demo/caching-lab';

/**
 * CachingLabDemo — the caching topic's lab (demo block id `caching:lab`).
 * One panel over the real cache-aside service: the state panel (key, live
 * TTL, counters), a fetch button that hits the REAL conditional endpoint
 * (x-cache flip miss → hit), a conditional console that runs the full
 * 200-then-If-None-Match round and shows the bodyless 304, an invalidate
 * button, and a stampede button whose counts prove single-flight. The
 * origin cost is simulated at 120 ms and labeled as such; the caching
 * around it is real.
 */

type LabStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: CachingLabModel };

type RoundStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'failed'; failure: Failure }
  | { state: 'done'; fresh: ConditionalRound; revalidated: ConditionalRound | null };

const STAMPEDE_SIZES = [4, 8, 16] as const;

export function CachingLabDemo() {
  const useCase = container.getCachingLabDemoUseCase;
  const [lab, setLab] = useState<LabStatus>({ state: 'loading' });
  const [round, setRound] = useState<RoundStatus>({ state: 'idle' });
  const [invalidate, setInvalidate] = useState<InvalidationOutcome | null>(null);
  const [stampede, setStampede] = useState<StampedeOutcome | null>(null);
  const [actionFailed, setActionFailed] = useState<Failure | null>(null);

  const refreshLab = useCallback(() => {
    void useCase.lab().then((result) => {
      setLab(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    refreshLab();
  }, [refreshLab]);

  /** Run one action, then refresh the state panel's counters. */
  function runAction<T>(action: () => Promise<Result<T>>, onDone: (value: T) => void): void {
    setActionFailed(null);
    void action().then((result) => {
      if (result.ok) {
        onDone(result.value);
        refreshLab();
      } else {
        setActionFailed(result.failure);
      }
    });
  };

  /** The fetch button: one conditional round against the real endpoint. */
  const fetchOnce = () => {
    setRound({ state: 'busy' });
    void useCase.conditionalRound().then((result) => {
      setRound(
        result.ok
          ? { state: 'done', fresh: result.value, revalidated: null }
          : { state: 'failed', failure: result.failure },
      );
      if (result.ok) refreshLab();
    });
  };

  /**
   * The conditional console: capture the current ETag with a fresh round,
   * then send it back — the second round is the 304 the topic teaches.
   */
  const runConditional = () => {
    setRound({ state: 'busy' });
    void useCase.conditionalRound().then((fresh) => {
      if (!fresh.ok) {
        setRound({ state: 'failed', failure: fresh.failure });
        return;
      }
      void useCase.conditionalRound(fresh.value.etag).then((revalidated) => {
        if (!revalidated.ok) {
          setRound({ state: 'failed', failure: revalidated.failure });
          return;
        }
        setRound({ state: 'done', fresh: fresh.value, revalidated: revalidated.value });
        refreshLab();
      });
    });
  };

  if (lab.state === 'loading') {
    return (
      <p data-testid="caching-lab-loading" className="text-body-sm text-on-surface-variant">
        reading the cache state…
      </p>
    );
  }

  if (lab.state === 'failed') {
    return <ErrorPanel subject="the caching lab" failure={lab.failure} onRetry={refreshLab} />;
  }

  const { data } = lab;
  const { state } = data;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="caching-lab-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">cache state · {state.key}</p>
        <p data-testid="caching-lab-liveness" className="font-mono text-caption text-on-surface">
          {state.present
            ? `entry live · ttl ${state.ttlRemainingS ?? 0}s of ${state.ttlSeconds}s${
                state.sizeBytes === null ? '' : ` · ${state.sizeBytes}B`
              }`
            : `no entry (ttl cap ${state.ttlSeconds}s) — next read is a miss`}
        </p>
        <p data-testid="caching-lab-telemetry" className="font-mono text-caption text-on-surface-variant">
          hits {state.telemetry.hits} · misses {state.telemetry.misses} · coalesced{' '}
          {state.telemetry.coalesced} · invalidations {state.telemetry.invalidations}
        </p>
        <p className="text-caption text-on-surface-variant">
          origin cost {data.originCostMs} ms — {data.originCostNote}.
        </p>
      </section>

      <div className="flex flex-wrap gap-xs">
        <button
          type="button"
          onClick={fetchOnce}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          GET {data.postsEndpoint}
        </button>
        <button
          type="button"
          onClick={runConditional}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          conditional round → 304
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.invalidate(), setInvalidate)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          invalidate
        </button>
        {STAMPEDE_SIZES.map((size) => (
          <button
            key={size}
            type="button"
            onClick={() => runAction(() => useCase.stampede(size), setStampede)}
            className="rounded-md border border-outline px-sm py-xxs font-mono text-caption hover:border-primary hover:text-primary"
          >
            stampede ×{size}
          </button>
        ))}
      </div>

      {actionFailed && (
        <p data-testid="caching-lab-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {round.state === 'busy' && (
        <p data-testid="caching-lab-round-busy" className="text-caption text-on-surface-variant">
          round-tripping the real endpoint…
        </p>
      )}
      {round.state === 'failed' && (
        <ErrorPanel subject="the conditional round" failure={round.failure} onRetry={runConditional} />
      )}
      {round.state === 'done' && (
        <section
          data-testid="caching-lab-round"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            conditional console · {data.postsEndpoint}
          </p>
          <RoundRow label="round 1 · fresh GET" round={round.fresh} />
          {round.revalidated && <RoundRow label="round 2 · If-None-Match sent back" round={round.revalidated} />}
          {round.revalidated && (
            <p data-testid="caching-lab-304-proof" className="font-mono text-caption text-on-surface">
              {round.revalidated.status === 304
                ? '304 · validators matched · 0 body bytes — the client keeps its copy'
                : `answered ${round.revalidated.status} — the representation changed in between`}
            </p>
          )}
        </section>
      )}

      {invalidate && (
        <section
          data-testid="caching-lab-invalidate"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">invalidation</p>
          <p className="font-mono text-caption text-on-surface">
            deleted {invalidate.deletedEntries} entr{invalidate.deletedEntries === 1 ? 'y' : 'ies'} —{' '}
            {invalidate.detail}
          </p>
        </section>
      )}

      {stampede && (
        <section
          data-testid="caching-lab-stampede"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">stampede · single-flight proof</p>
          <p data-testid="caching-lab-stampede-counts" className="font-mono text-caption text-on-surface">
            {stampede.requests} requests → origin fetches {stampede.originFetches} · served warm{' '}
            {stampede.servedWarm} · wall {stampede.wallMs}ms
          </p>
          <p className="text-caption text-on-surface-variant">{stampede.proof}</p>
        </section>
      )}

      <p data-testid="caching-lab-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function RoundRow({ label, round }: { label: string; round: ConditionalRound }) {
  return (
    <p className="font-mono text-caption text-on-surface-variant">
      {label}: {round.status} · x-cache {round.cache} · {round.elapsedMs}ms · etag {round.etag} ·{' '}
      {round.bodyBytes}B
    </p>
  );
}

export default CachingLabDemo;
