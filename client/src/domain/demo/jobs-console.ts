/** Domain types for the jobs console demo (demo id `jobs:console`). */

/** The console's retry policy, exact: budget, curve, where attempts run. */
export interface JobsPolicy {
  maxAttempts: number;
  strategy: string;
  baseDelaySeconds: number;
  delayBetweenAttempts: number[];
  attemptOffsets: number[];
}

/** One registered task the panel can fire (the worker's name table). */
export interface JobSpec {
  name: string;
  behavior: string;
  expectedAttempts: number;
  pacedSeconds: number | null;
  takesPayload: boolean;
  teaches: string;
}

/** One demo endpoint the panel advertises. */
export interface JobsEndpointRow {
  path: string;
  method: string;
  teaches: string;
}

/** GET /api/demo/jobs/console — the panel payload. */
export interface JobsPanel {
  policy: JobsPolicy;
  catalog: JobSpec[];
  queueKeys: string;
  demoNamespace: string;
  workerCommand: string;
  cronSchedule: string;
  endpoints: JobsEndpointRow[];
  honestyNotes: string[];
  reasoning: string;
}

/** One enqueue's receipt: the id to poll and where it went. */
export interface JobTicket {
  jobId: string;
  functionName: string;
  enqueuedAtMs: number;
}

/** How one attempt ended: done, rescheduled by the policy, or dead-lettered. */
export type AttemptOutcome = 'succeeded' | 'retry_scheduled' | 'failed_final';

/** One attempt on the trail the worker writes per job. */
export interface AttemptStep {
  attempt: number;
  outcome: AttemptOutcome;
  detail: string;
  atMs: number;
}

/** The job lifecycle as the console reports it (arq's states + the terminal split). */
export type JobStatusName =
  | 'deferred'
  | 'queued'
  | 'in_progress'
  | 'complete'
  | 'failed'
  | 'not_found';

/** One job's whole story: lifecycle state, the attempt trail, the verdict. */
export interface JobSnapshot {
  jobId: string;
  status: JobStatusName;
  attempts: AttemptStep[];
  result: string | null;
  deadLettered: boolean;
}

/** The two observability numbers: queue depth and the oldest job's age. */
export interface QueueStats {
  depth: number;
  oldestAgeSeconds: number | null;
}

/** One parked job: why it died, how hard it was tried, its replay link. */
export interface DeadLetterEntry {
  entryId: string;
  jobId: string;
  functionName: string;
  attempts: number;
  reason: string;
  failedAtMs: number;
  payload: string;
  replayedAs: string | null;
}

/** GET /api/demo/jobs/dlq — the parking lot plus its replay semantics. */
export interface DeadLetterPanel {
  entries: DeadLetterEntry[];
  detail: string;
}

/** One recorded email — the demo's mailbox has no SMTP (topic 42 wires one). */
export interface MailboxMessage {
  messageId: string;
  to: string;
  subject: string;
  body: string;
  sentAtMs: number;
  jobId: string;
}

/** GET /api/demo/jobs/mailbox — the recorded emails. */
export interface MailboxPanel {
  entries: MailboxMessage[];
  detail: string;
}

/** The cron heartbeat: when it last beat, how many beats so far. */
export interface Heartbeat {
  lastRunMs: number | null;
  beats: number;
  schedule: string;
}

/** One side of one comparison run: where the work ran and how long. */
export interface ComparisonRun {
  runId: string;
  side: 'in_process' | 'queued';
  ranOn: string;
  handoffDurationMs: number;
  workDurationMs: number;
  finishedAtMs: number;
}

/** POST /api/demo/jobs/compare — both halves fired, honestly timed. */
export interface CompareFired {
  runId: string;
  queuedJobId: string;
  handlerDurationMs: number;
}

/** GET /api/demo/jobs/compare — the comparison ledger, newest first. */
export interface ComparisonPanel {
  runs: ComparisonRun[];
  detail: string;
}
