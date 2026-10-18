import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  SliceOutcome,
  SliceRunResult,
  TestingRunnerData,
} from '../../../domain/demo/testing-runner';

/**
 * TestingRunnerDemo — the testing topic's live runner (demo block id
 * `testing:runner`). The roster loads on mount: four curated slices of
 * the SERVER repo's own test files, the client suite's honest recipe
 * row, and the mechanics (argv template, cwd, timeout, off-loop, guard
 * env). Pressing a slice's run button fires a REAL subprocess pytest
 * round through the server; the result card renders genuine counts,
 * wall-clock and pytest durations, the raw summary line, the exact
 * command, and per-test lines. The testcontainers slice showing its
 * honest skips (no docker.sock in this container) is the exhibit — the
 * panel never fakes a run it did not make.
 *
 * Dependency flow mirrors the other demos: the use case resolves from
 * the container at render time (specs substitute fakes through the
 * container token), failures arrive as typed Failures inside Results,
 * and the shared ErrorPanel offers recovery.
 */

type RosterStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: TestingRunnerData }
  | { state: 'error'; failure: Failure };

type RunStatus =
  | { state: 'idle' }
  | { state: 'running' }
  | { state: 'done'; result: SliceRunResult }
  | { state: 'error'; failure: Failure };

export function TestingRunnerDemo() {
  const useCase = container.getTestingRunnerDemoUseCase;
  const [roster, setRoster] = useState<RosterStatus>({ state: 'loading' });
  const [runs, setRuns] = useState<Record<string, RunStatus>>({});

  const loadRoster = useCallback(() => {
    setRoster({ state: 'loading' });
    void useCase.execute().then((result) => {
      setRoster(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    loadRoster();
  }, [loadRoster]);

  const fire = (sliceId: string) => {
    setRuns((current) => ({ ...current, [sliceId]: { state: 'running' } }));
    void useCase.run(sliceId).then((result) => {
      setRuns((current) => ({
        ...current,
        [sliceId]: result.ok
          ? { state: 'done', result: result.value }
          : { state: 'error', failure: result.failure },
      }));
    });
  };

  if (roster.state === 'loading') {
    return (
      <p data-testid="tr-loading" className="text-body-sm text-on-surface-variant">
        loading the roster…
      </p>
    );
  }

  if (roster.state === 'error') {
    return (
      <ErrorPanel subject="the testing runner" failure={roster.failure} onRetry={loadRoster} />
    );
  }

  const { slices, clientRecipe, facts, reasoning } = roster.data;

  return (
    <div className="flex flex-col gap-md">
      <p data-testid="tr-facts" className="font-mono text-caption text-on-surface-variant">
        {facts.commandTemplate} · cwd {facts.cwd} · timeout {facts.timeoutSeconds}s ·{' '}
        {facts.offLoop} · guard {facts.guardEnv}
      </p>

      {slices.map((slice) => {
        const status: RunStatus = runs[slice.sliceId] ?? { state: 'idle' };
        return (
          <div key={slice.sliceId} data-testid={`tr-slice-${slice.sliceId}`} className="flex flex-col gap-xxs">
            <div className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
              <div className="flex flex-wrap items-baseline gap-xs">
                <span className="font-mono text-caption uppercase tracking-wide text-primary">
                  {slice.title}
                </span>
                <span className="text-caption text-on-surface-variant">{slice.focus}</span>
                <button
                  type="button"
                  data-testid={`tr-run-${slice.sliceId}`}
                  onClick={() => fire(slice.sliceId)}
                  disabled={status.state === 'running'}
                  className="ml-auto self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {status.state === 'running' ? 'running…' : 'Run slice'}
                </button>
              </div>
              <p className="font-mono text-caption text-on-surface-variant">{slice.paths.join(' ')}</p>
              <p className="text-caption text-on-surface-variant">{slice.note}</p>
            </div>

            {status.state === 'running' && (
              <p data-testid={`tr-pending-${slice.sliceId}`} className="text-caption text-on-surface-variant">
                running pytest in a subprocess…
              </p>
            )}
            {status.state === 'done' && <RunResult result={status.result} />}
            {status.state === 'error' && (
              <ErrorPanel
                subject={`the ${slice.sliceId} slice`}
                failure={status.failure}
                onRetry={() => fire(slice.sliceId)}
              />
            )}
          </div>
        );
      })}

      <div
        data-testid="tr-recipe"
        className="flex flex-col gap-xxs rounded-md border border-outline bg-surface-tint px-sm py-xs"
      >
        <p className="text-body-sm text-on-surface">{clientRecipe.title}</p>
        <p className="font-mono text-caption text-on-surface">{clientRecipe.command}</p>
        <p className="text-caption text-on-surface-variant">{clientRecipe.note}</p>
      </div>

      <p data-testid="tr-reasoning" className="text-body-sm text-on-surface-variant">
        {reasoning}
      </p>
    </div>
  );
}

function RunResult({ result }: { result: SliceRunResult }) {
  return (
    <div
      data-testid={`tr-result-${result.sliceId}`}
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="flex flex-wrap items-baseline gap-xs font-mono text-caption text-on-surface">
        <span className={outcomeClass(result.outcome)}>{result.outcome}</span>
        <span>passed {result.passed}</span>
        <span>failed {result.failed}</span>
        <span>skipped {result.skipped}</span>
        <span className="text-on-surface-variant">wall {result.durationMs}ms</span>
        {result.pytestSeconds !== undefined && (
          <span className="text-on-surface-variant">pytest {result.pytestSeconds}s</span>
        )}
      </p>
      <p className="font-mono text-caption text-on-surface">{result.summaryLine}</p>
      <p className="font-mono text-caption text-on-surface-variant">{result.commandLine}</p>
      {result.testLines.slice(0, 6).map((line) => (
        <p key={line.nodeid} className="flex items-baseline gap-xs font-mono text-caption">
          <span className={outcomeClass(line.outcome)}>{line.outcome}</span>
          <span className="text-on-surface-variant">{line.nodeid}</span>
        </p>
      ))}
      {result.testLines.length > 6 && (
        <p className="text-caption text-on-surface-variant">
          … {result.testLines.length - 6} more test lines
        </p>
      )}
      <p className="text-caption text-on-surface-variant">{result.note}</p>
    </div>
  );
}

function outcomeClass(outcome: SliceOutcome | string): string {
  if (outcome === 'passed') {
    return 'rounded-pill border border-primary px-sm py-xxs uppercase tracking-wide text-primary';
  }
  if (outcome === 'failed' || outcome === 'error' || outcome === 'internal_error') {
    return 'rounded-pill border border-secondary px-sm py-xxs uppercase tracking-wide text-secondary';
  }
  return 'rounded-pill border border-outline px-sm py-xxs uppercase tracking-wide text-on-surface-variant';
}

export default TestingRunnerDemo;
