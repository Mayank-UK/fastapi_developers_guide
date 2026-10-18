import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ConsoleDemo } from './console_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetJobsConsoleDemoUseCase } from '../../../domain/demo/get-jobs-console-demo-usecase';
import type {
  DeadLetterPanel,
  JobSnapshot,
  JobTicket,
  JobsPanel,
  MailboxPanel,
  QueueStats,
} from '../../../domain/demo/jobs-console';

/**
 * ConsoleDemo spec — fixture-driven (happy + failure): the panel renders
 * the policy schedule and the catalog buttons; an enqueue polls the job's
 * snapshot and renders the attempt trail (the retry visible); the DLQ
 * lists parked jobs with a replay button; the comparison shows both
 * homes' honest timings; a Failed panel degrades to the shared error
 * panel with recovery.
 */

const panel: JobsPanel = {
  policy: {
    maxAttempts: 3,
    strategy: 'exponential',
    baseDelaySeconds: 0.25,
    delayBetweenAttempts: [0.25, 0.5],
    attemptOffsets: [0, 0.25, 0.75],
  },
  catalog: [
    { name: 'fast', behavior: 'succeeds-first-try', expectedAttempts: 1, pacedSeconds: null, takesPayload: false, teaches: 'the happy path' },
    { name: 'fail_once', behavior: 'succeeds-on-retry', expectedAttempts: 2, pacedSeconds: null, takesPayload: false, teaches: 'the retry made visible' },
    { name: 'fail_always', behavior: 'exhausts-retries', expectedAttempts: 3, pacedSeconds: null, takesPayload: false, teaches: 'the budget edge' },
  ],
  queueKeys: 'arq:*',
  demoNamespace: 'guide_demo:jobs:*',
  workerCommand: 'arq guide.worker.WorkerSettings',
  cronSchedule: 'heartbeat: every minute (arq cron) + once at worker boot',
  endpoints: [],
  honestyNotes: ['every button lands on the real broker (redis) and the real worker process'],
  reasoning: 'one policy engine decides every retry',
};

const ticket: JobTicket = { jobId: 'job-42', functionName: 'fail_once', enqueuedAtMs: 1000 };

const walked: JobSnapshot = {
  jobId: 'job-42',
  status: 'complete',
  attempts: [
    { attempt: 1, outcome: 'retry_scheduled', detail: 'policy schedules attempt 2 in 0.25s', atMs: 1100 },
    { attempt: 2, outcome: 'succeeded', detail: 'attempt 2 landed — the retry worked', atMs: 1500 },
  ],
  result: 'attempt 2 landed — the retry worked',
  deadLettered: false,
};

const dlq: DeadLetterPanel = {
  entries: [
    {
      entryId: 'e1',
      jobId: 'job-7',
      functionName: 'fail_always',
      attempts: 3,
      reason: 'attempt budget spent: 3/3 tries on the exponential curve',
      failedAtMs: 2000,
      payload: '',
      replayedAs: null,
    },
  ],
  detail: 'replay re-enqueues fresh',
};

const mailbox: MailboxPanel = {
  entries: [{ messageId: 'm1', to: 'ada@example.com', subject: 'hello', body: '', sentAtMs: 3000, jobId: 'job-9' }],
  detail: 'no SMTP here',
};

const stats: QueueStats = { depth: 1, oldestAgeSeconds: 2.5 };

type Stubs = {
  panel?: () => Promise<Result<JobsPanel>>;
  enqueue?: (name: string) => Promise<Result<JobTicket>>;
  snapshot?: (jobId: string) => Promise<Result<JobSnapshot>>;
  replay?: (entryId: string) => Promise<Result<JobTicket>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetJobsConsoleDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    enqueue: stubs.enqueue ?? (async () => success(ticket)),
    snapshot: stubs.snapshot ?? (async () => success(walked)),
    stats: async () => success(stats),
    deadLetters: async () => success(dlq),
    replay: stubs.replay ?? (async () => success({ ...ticket, jobId: 'job-99', functionName: 'fail_always' })),
    mailbox: async () => success(mailbox),
    sendMail: async () => success({ ...ticket, functionName: 'send_email' }),
    heartbeat: async () => success({ lastRunMs: 5000, beats: 6, schedule: 'every minute' }),
    compare: async () => success({ runId: 'run-1', queuedJobId: 'job-11', handlerDurationMs: 1.2 }),
    comparison: async () =>
      success({
        runs: [
          { runId: 'run-1', side: 'queued', ranOn: 'arq worker process', handoffDurationMs: 415, workDurationMs: 637, finishedAtMs: 9000 },
          { runId: 'run-1', side: 'in_process', ranOn: 'server process — starlette BackgroundTasks', handoffDurationMs: 2, workDurationMs: 612, finishedAtMs: 8600 },
        ],
        detail: 'handoff = decision-to-work-start',
      }),
  } as unknown as GetJobsConsoleDemoUseCase);
}

describe('ConsoleDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['jobs:console']).toBeDefined();
  });

  it('renders the policy schedule, the catalog buttons, and the two numbers', async () => {
    stubUseCase({});
    render(<ConsoleDemo />);

    const policy = await screen.findByTestId('jobs-console-policy');
    expect(policy).toHaveTextContent('3 attempts');
    expect(policy).toHaveTextContent('0s / 0.25s / 0.75s');
    expect(policy).toHaveTextContent('arq guide.worker.WorkerSettings');
    expect(screen.getByRole('button', { name: 'enqueue fast' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'enqueue fail_once' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('jobs-console-stats')).toHaveTextContent('depth 1');
    });
    expect(screen.getByTestId('jobs-console-stats')).toHaveTextContent('oldest 2.5s');
    expect(screen.getByTestId('jobs-console-stats')).toHaveTextContent('6 beats');
  });

  it('renders the retried job’s attempt trail when an enqueue lands', async () => {
    stubUseCase({});
    render(<ConsoleDemo />);

    fireEvent.click(await screen.findByRole('button', { name: 'enqueue fail_once' }));
    const job = await screen.findByTestId('jobs-console-job');
    await waitFor(() => {
      expect(job).toHaveTextContent('status: complete');
    });
    expect(job).toHaveTextContent('attempt 1: retry_scheduled');
    expect(job).toHaveTextContent('attempt 2: succeeded');
  });

  it('lists the parked jobs with a replay button and replays fresh', async () => {
    stubUseCase({});
    render(<ConsoleDemo />);

    const dlqSection = await screen.findByTestId('jobs-console-dlq');
    expect(dlqSection).toHaveTextContent('fail_always');
    expect(dlqSection).toHaveTextContent('3 attempts');

    fireEvent.click(screen.getByRole('button', { name: 'replay' }));
    await waitFor(() => {
      expect(screen.getByTestId('jobs-console-notice')).toHaveTextContent(
        'replayed as job-99 — attempts reset to 1',
      );
    });
  });

  it('fires the comparison and renders both homes with honest timings', async () => {
    stubUseCase({});
    render(<ConsoleDemo />);

    fireEvent.click(await screen.findByRole('button', { name: /fire comparison/ }));
    const compareSection = screen.getByTestId('jobs-console-compare');
    await waitFor(() => {
      expect(compareSection).toHaveTextContent('fired in 1.2ms');
    });
    await waitFor(() => {
      expect(compareSection).toHaveTextContent('in-process: handoff 2.0ms');
    });
    expect(compareSection).toHaveTextContent('queued: handoff 415.0ms');
    expect(compareSection).toHaveTextContent('starlette BackgroundTasks');
  });

  it('degrades to the shared error panel when the panel fails', async () => {
    stubUseCase({ panel: async () => failed(new ServerFailure('redis is away')) });
    render(<ConsoleDemo />);

    const error = await screen.findByRole('alert');
    expect(error).toHaveTextContent('redis is away');
  });
});
