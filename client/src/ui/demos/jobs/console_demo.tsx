import { useCallback, useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type {
  ComparisonRun,
  DeadLetterPanel,
  JobSnapshot,
  JobTicket,
  JobsPanel,
  MailboxPanel,
  QueueStats,
  Heartbeat as HeartbeatRow,
} from '../../../domain/demo/jobs-console';
import { ErrorPanel } from '../../components/error-panel';

/**
 * ConsoleDemo — the background-jobs topic's lab (demo id `jobs:console`).
 * The LIVE queue is the demo: every button lands on the real broker and
 * the real worker container — enqueue a task and watch its attempt trail
 * fill (fail_once shows the policy's retry; fail_always walks the whole
 * budget into the dead-letter queue), poll the two observability numbers,
 * replay a parked job (fresh id, attempts reset), compose an email that
 * records in the mailbox (or parks as poison with a not-an-address), and
 * fire the comparison that times the same workload in-process (BackgroundTasks)
 * and queued (worker) with honest handoff numbers.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: JobsPanel };

const STATS_POLL_MS = 1500;
const SNAPSHOT_POLL_MS = 700;
const TERMINAL = new Set(['complete', 'failed', 'not_found']);

const buttonClass =
  'w-fit rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50';
const inputClass =
  'rounded-md border border-outline bg-surface px-sm py-xxs text-caption text-on-surface';

function outcomeColor(outcome: string): string {
  if (outcome === 'succeeded') return 'text-primary';
  if (outcome === 'failed_final') return 'text-error';
  return 'text-on-surface-variant';
}

function describeStats(stats: QueueStats | null): string {
  if (!stats) return '';
  const age = stats.oldestAgeSeconds === null ? '—' : `${stats.oldestAgeSeconds.toFixed(1)}s`;
  return `queue: depth ${stats.depth} · oldest ${age}`;
}

export function ConsoleDemo() {
  const useCase = container.getJobsConsoleDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [selected, setSelected] = useState<{ name: string; ticket: JobTicket } | null>(null);
  const [snapshot, setSnapshot] = useState<JobSnapshot | null>(null);
  const [dlq, setDlq] = useState<DeadLetterPanel | null>(null);
  const [mailbox, setMailbox] = useState<MailboxPanel | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatRow | null>(null);
  const [compare, setCompare] = useState<{ runId: string; firedMs: number } | null>(null);
  const [runs, setRuns] = useState<ComparisonRun[]>([]);
  const [mailTo, setMailTo] = useState('ada@example.com');
  const [mailSubject, setMailSubject] = useState('hello from the console');
  const [notice, setNotice] = useState('');
  const pollRef = useRef<number | null>(null);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      if (result.ok) setPanel({ state: 'ready', data: result.value });
      else setPanel({ state: 'failed', failure: result.failure });
    });
  }, [useCase]);

  const refreshSidePanels = useCallback(() => {
    void useCase.deadLetters().then((r) => r.ok && setDlq(r.value));
    void useCase.mailbox().then((r) => r.ok && setMailbox(r.value));
    void useCase.heartbeat().then((r) => r.ok && setHeartbeat(r.value));
    void useCase.comparison().then((r) => r.ok && setRuns(r.value.runs));
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
    refreshSidePanels();
  }, [refreshPanel, refreshSidePanels]);

  // The two numbers, polled while the demo is on screen (first read now).
  useEffect(() => {
    const read = (): void => {
      void useCase.stats().then((r) => r.ok && setStats(r.value));
    };
    read();
    const timer = window.setInterval(read, STATS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [useCase]);

  useEffect(() => () => {
    if (pollRef.current !== null) window.clearInterval(pollRef.current);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollJob = useCallback(
    (jobId: string) => {
      stopPolling();
      const tick = (): void => {
        void useCase.snapshot(jobId).then((r) => {
          if (!r.ok) return; // transient poll trouble: the next tick retries
          setSnapshot(r.value);
          if (TERMINAL.has(r.value.status)) {
            stopPolling();
            refreshSidePanels();
          }
        });
      };
      tick();
      pollRef.current = window.setInterval(tick, SNAPSHOT_POLL_MS);
    },
    [useCase, stopPolling, refreshSidePanels],
  );

  function enqueue(name: string): void {
    setNotice(`enqueued ${name}…`);
    void useCase.enqueue(name).then((r) => {
      if (!r.ok) {
        setNotice(`enqueue failed: ${r.failure.message}`);
        return;
      }
      setSelected({ name, ticket: r.value });
      setSnapshot(null);
      pollJob(r.value.jobId);
    });
  }

  function replay(entryId: string): void {
    void useCase.replay(entryId).then((r) => {
      if (!r.ok) {
        setNotice(`replay failed: ${r.failure.message}`);
        return;
      }
      setNotice(`replayed as ${r.value.jobId} — attempts reset to 1`);
      setSelected({ name: r.value.functionName, ticket: r.value });
      setSnapshot(null);
      pollJob(r.value.jobId);
    });
  }

  function sendMail(): void {
    void useCase.sendMail(mailTo, mailSubject).then((r) => {
      if (!r.ok) {
        setNotice(`compose failed: ${r.failure.message}`);
        return;
      }
      setSelected({ name: 'send_email', ticket: r.value });
      setSnapshot(null);
      setNotice(
        mailTo.includes('@') && mailTo.includes('.')
          ? 'email job enqueued — watch the mailbox'
          : 'poison draft accepted — watch it park in the DLQ after ONE attempt',
      );
      pollJob(r.value.jobId);
    });
  }

  function fireComparison(): void {
    void useCase.compare().then((r) => {
      if (!r.ok) {
        setNotice(`comparison failed: ${r.failure.message}`);
        return;
      }
      setCompare({ runId: r.value.runId, firedMs: r.value.handlerDurationMs });
      window.setTimeout(refreshSidePanels, 2500);
    });
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="jobs-console-loading" className="text-body-sm text-on-surface-variant">
        opening the jobs console…
      </p>
    );
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel subject="the jobs console" failure={panel.failure} onRetry={refreshPanel} />
    );
  }

  const { policy, catalog } = panel.data;
  const lastRun = compare ? runs.filter((run) => run.runId === compare.runId) : runs.slice(0, 2);

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="jobs-console-policy" className="flex flex-col gap-xxs">
        <p className="font-mono text-caption text-on-surface">
          policy: {policy.maxAttempts} attempts · {policy.strategy} · base{' '}
          {policy.baseDelaySeconds}s — attempts at offsets{' '}
          {policy.attemptOffsets.map((o) => `${o}s`).join(' / ')}
        </p>
        <p className="font-mono text-caption text-on-surface">
          worker: {panel.data.workerCommand} · cron: {panel.data.cronSchedule}
        </p>
        {panel.data.honestyNotes.map((note) => (
          <p key={note} className="text-caption text-on-surface-variant">
            · {note}
          </p>
        ))}
      </section>

      <p data-testid="jobs-console-stats" className="font-mono text-caption text-on-surface">
        {describeStats(stats)}
        {heartbeat
          ? ` · heartbeat: ${heartbeat.beats} beats${
              heartbeat.lastRunMs !== null
                ? `, last ${new Date(heartbeat.lastRunMs).toLocaleTimeString()}`
                : ''
            }`
          : ''}
      </p>

      <section data-testid="jobs-console-controls" className="flex flex-wrap gap-xs">
        {catalog.map((spec) => (
          <button
            key={spec.name}
            type="button"
            className={buttonClass}
            onClick={() => enqueue(spec.name)}
            title={spec.teaches}
          >
            enqueue {spec.name}
          </button>
        ))}
      </section>

      {notice && (
        <p data-testid="jobs-console-notice" className="text-caption text-on-surface-variant">
          {notice}
        </p>
      )}

      <section data-testid="jobs-console-job" className="flex flex-col gap-xxs">
        {selected && snapshot ? (
          <>
            <p className="font-mono text-caption text-on-surface">
              {selected.ticket.functionName} · {snapshot.jobId.slice(0, 8)} · status:{' '}
              <span
                className={
                  snapshot.status === 'complete'
                    ? 'text-primary'
                    : snapshot.status === 'failed'
                      ? 'text-error'
                      : 'text-on-surface-variant'
                }
              >
                {snapshot.status}
              </span>
              {snapshot.deadLettered ? ' · dead-lettered' : ''}
            </p>
            {snapshot.attempts.map((step) => (
              <p key={step.attempt} className="font-mono text-caption">
                <span className={outcomeColor(step.outcome)}>
                  attempt {step.attempt}: {step.outcome}
                </span>{' '}
                — {step.detail}
              </p>
            ))}
          </>
        ) : (
          <p className="text-caption text-on-surface-variant">
            (no job selected — enqueue one and watch its attempt trail fill)
          </p>
        )}
      </section>

      <section data-testid="jobs-console-dlq" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface">dead letters ({dlq?.entries.length ?? 0})</p>
        {dlq?.entries.length === 0 && (
          <p className="text-caption text-on-surface-variant">(empty — enqueue fail_always)</p>
        )}
        {dlq?.entries.map((entry) => (
          <p key={entry.entryId} className="font-mono text-caption">
            {entry.functionName} · {entry.attempts} attempts · {entry.reason.slice(0, 60)}{' '}
            {entry.replayedAs ? (
              <span className="text-primary">· replayed as {entry.replayedAs.slice(0, 8)}</span>
            ) : (
              <button type="button" className={buttonClass} onClick={() => replay(entry.entryId)}>
                replay
              </button>
            )}
          </p>
        ))}
      </section>

      <section data-testid="jobs-console-mailbox" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface">
          mailbox ({mailbox?.entries.length ?? 0}) — no SMTP; the pattern is the lesson
        </p>
        <div className="flex flex-wrap gap-xs">
          <input
            className={inputClass}
            value={mailTo}
            onChange={(e) => setMailTo(e.target.value)}
            aria-label="email recipient"
          />
          <input
            className={inputClass}
            value={mailSubject}
            onChange={(e) => setMailSubject(e.target.value)}
            aria-label="email subject"
          />
          <button type="button" className={buttonClass} onClick={sendMail}>
            compose + enqueue
          </button>
        </div>
        {mailbox?.entries.map((message) => (
          <p key={message.messageId} className="font-mono text-caption">
            to {message.to} — {message.subject}
          </p>
        ))}
      </section>

      <section data-testid="jobs-console-compare" className="flex flex-col gap-xxs">
        <div className="flex flex-wrap items-center gap-xs">
          <button type="button" className={buttonClass} onClick={fireComparison}>
            fire comparison (same workload, two homes)
          </button>
          {compare && (
            <span className="font-mono text-caption text-on-surface-variant">
              fired in {compare.firedMs.toFixed(1)}ms · run {compare.runId}
            </span>
          )}
        </div>
        {lastRun.map((run) => (
          <p key={`${run.runId}-${run.side}`} className="font-mono text-caption">
            {run.side === 'in_process' ? 'in-process' : 'queued'}: handoff{' '}
            {run.handoffDurationMs.toFixed(1)}ms · work {run.workDurationMs.toFixed(1)}ms —{' '}
            {run.ranOn}
          </p>
        ))}
      </section>
    </div>
  );
}

export default ConsoleDemo;
