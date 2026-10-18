import type {
  AttemptOutcome,
  AttemptStep,
  CompareFired,
  ComparisonPanel,
  ComparisonRun,
  DeadLetterEntry,
  DeadLetterPanel,
  Heartbeat,
  JobSnapshot,
  JobStatusName,
  JobTicket,
  JobsEndpointRow,
  JobsPanel,
  JobsPolicy,
  JobSpec,
  MailboxMessage,
  MailboxPanel,
  QueueStats,
} from '../../domain/demo/jobs-console';
import {
  isRecord,
  optionalNumber,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * JobsConsoleDTO — the wire/transport shapes of the jobs console's
 * endpoints, validated field-by-field so a shape violation surfaces as a
 * typed invalid_response failure instead of "[object Object]" reaching the
 * UI. The only nulls on the wire are honest ones: `oldestAgeSeconds` (an
 * empty queue has no oldest job), `lastRunMs` (a worker that never beat),
 * `pacedSeconds`/`result`/`replayedAs` (absent by meaning).
 */

const ATTEMPT_OUTCOMES: readonly string[] = ['succeeded', 'retry_scheduled', 'failed_final'];
const JOB_STATUSES: readonly string[] = [
  'deferred',
  'queued',
  'in_progress',
  'complete',
  'failed',
  'not_found',
];

function numberOrNull(source: Record<string, unknown>, key: string): number | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'number') throw new Error(`${key} must be a number or null`);
  return value;
}

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`${key} must be a string or null`);
  return value;
}

function oneOf(value: unknown, allowed: readonly string[], label: string): string {
  if (typeof value !== 'string' || !allowed.includes(value)) {
    throw new Error(`${label} must be one of ${allowed.join(', ')}`);
  }
  return value;
}

function ticketFromJson(value: unknown): JobTicket {
  if (!isRecord(value)) throw new Error('job ticket must be an object');
  return {
    jobId: requiredString(value, 'jobId'),
    functionName: requiredString(value, 'functionName'),
    enqueuedAtMs: requiredNumber(value, 'enqueuedAtMs'),
  };
}

function attemptFromJson(value: unknown): AttemptStep {
  if (!isRecord(value)) throw new Error('attempt step must be an object');
  return {
    attempt: requiredNumber(value, 'attempt'),
    outcome: oneOf(value['outcome'], ATTEMPT_OUTCOMES, 'attempt outcome') as AttemptOutcome,
    detail: requiredString(value, 'detail'),
    atMs: requiredNumber(value, 'atMs'),
  };
}

function snapshotFromJson(value: unknown): JobSnapshot {
  if (!isRecord(value)) throw new Error('job snapshot must be an object');
  return {
    jobId: requiredString(value, 'jobId'),
    status: oneOf(value['status'], JOB_STATUSES, 'job status') as JobStatusName,
    attempts: requiredArray(value, 'attempts').map(attemptFromJson),
    result: stringOrNull(value, 'result'),
    deadLettered: value['deadLettered'] === true,
  };
}

function statsFromJson(value: unknown): QueueStats {
  if (!isRecord(value)) throw new Error('queue stats must be an object');
  return {
    depth: requiredNumber(value, 'depth'),
    oldestAgeSeconds: numberOrNull(value, 'oldestAgeSeconds'),
  };
}

function deadLetterFromJson(value: unknown): DeadLetterEntry {
  if (!isRecord(value)) throw new Error('dead-letter entry must be an object');
  return {
    entryId: requiredString(value, 'entryId'),
    jobId: requiredString(value, 'jobId'),
    functionName: requiredString(value, 'functionName'),
    attempts: requiredNumber(value, 'attempts'),
    reason: requiredString(value, 'reason'),
    failedAtMs: requiredNumber(value, 'failedAtMs'),
    payload: requiredString(value, 'payload'),
    replayedAs: stringOrNull(value, 'replayedAs'),
  };
}

function mailboxMessageFromJson(value: unknown): MailboxMessage {
  if (!isRecord(value)) throw new Error('mailbox message must be an object');
  return {
    messageId: requiredString(value, 'messageId'),
    to: requiredString(value, 'to'),
    subject: requiredString(value, 'subject'),
    body: requiredString(value, 'body'),
    sentAtMs: requiredNumber(value, 'sentAtMs'),
    jobId: requiredString(value, 'jobId'),
  };
}

function comparisonRunFromJson(value: unknown): ComparisonRun {
  if (!isRecord(value)) throw new Error('comparison run must be an object');
  return {
    runId: requiredString(value, 'runId'),
    side: oneOf(value['side'], ['in_process', 'queued'], 'comparison side') as ComparisonRun['side'],
    ranOn: requiredString(value, 'ranOn'),
    handoffDurationMs: requiredNumber(value, 'handoffDurationMs'),
    workDurationMs: requiredNumber(value, 'workDurationMs'),
    finishedAtMs: requiredNumber(value, 'finishedAtMs'),
  };
}

/** Deserialize + validate the console panel. */
export function jobsPanelFromJson(body: unknown): JobsPanel {
  if (!isRecord(body)) throw new Error('jobs panel must be an object');
  const policy = body['policy'];
  if (!isRecord(policy)) throw new Error('policy must be an object');
  const parsedPolicy: JobsPolicy = {
    maxAttempts: requiredNumber(policy, 'maxAttempts'),
    strategy: requiredString(policy, 'strategy'),
    baseDelaySeconds: requiredNumber(policy, 'baseDelaySeconds'),
    delayBetweenAttempts: requiredArray(policy, 'delayBetweenAttempts').map((v) => {
      if (typeof v !== 'number') throw new Error('delays must be numbers');
      return v;
    }),
    attemptOffsets: requiredArray(policy, 'attemptOffsets').map((v) => {
      if (typeof v !== 'number') throw new Error('offsets must be numbers');
      return v;
    }),
  };
  const catalog = requiredArray(body, 'catalog').map((entry): JobSpec => {
    if (!isRecord(entry)) throw new Error('catalog entry must be an object');
    return {
      name: requiredString(entry, 'name'),
      behavior: requiredString(entry, 'behavior'),
      expectedAttempts: requiredNumber(entry, 'expectedAttempts'),
      pacedSeconds: numberOrNull(entry, 'pacedSeconds'),
      takesPayload: entry['takesPayload'] === true,
      teaches: requiredString(entry, 'teaches'),
    };
  });
  const endpoints = requiredArray(body, 'endpoints').map((entry): JobsEndpointRow => {
    if (!isRecord(entry)) throw new Error('endpoint row must be an object');
    return {
      path: requiredString(entry, 'path'),
      method: requiredString(entry, 'method'),
      teaches: requiredString(entry, 'teaches'),
    };
  });
  const honestyNotes = requiredArray(body, 'honestyNotes').map((note) => {
    if (typeof note !== 'string') throw new Error('honesty notes must be strings');
    return note;
  });
  return {
    policy: parsedPolicy,
    catalog,
    queueKeys: requiredString(body, 'queueKeys'),
    demoNamespace: requiredString(body, 'demoNamespace'),
    workerCommand: requiredString(body, 'workerCommand'),
    cronSchedule: requiredString(body, 'cronSchedule'),
    endpoints,
    honestyNotes,
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate a job ticket. */
export function jobTicketFromJson(body: unknown): JobTicket {
  return ticketFromJson(body);
}

/** Deserialize + validate a job snapshot. */
export function jobSnapshotFromJson(body: unknown): JobSnapshot {
  return snapshotFromJson(body);
}

/** Deserialize + validate the two numbers. */
export function queueStatsFromJson(body: unknown): QueueStats {
  return statsFromJson(body);
}

/** Deserialize + validate the dead-letter panel. */
export function deadLetterPanelFromJson(body: unknown): DeadLetterPanel {
  if (!isRecord(body)) throw new Error('dead-letter panel must be an object');
  return {
    entries: requiredArray(body, 'entries').map(deadLetterFromJson),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the mailbox panel. */
export function mailboxPanelFromJson(body: unknown): MailboxPanel {
  if (!isRecord(body)) throw new Error('mailbox panel must be an object');
  return {
    entries: requiredArray(body, 'entries').map(mailboxMessageFromJson),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the heartbeat. */
export function heartbeatFromJson(body: unknown): Heartbeat {
  if (!isRecord(body)) throw new Error('heartbeat must be an object');
  return {
    lastRunMs: numberOrNull(body, 'lastRunMs'),
    beats: optionalNumber(body, 'beats') ?? 0,
    schedule: requiredString(body, 'schedule'),
  };
}

/** Deserialize + validate a fired comparison. */
export function compareFiredFromJson(body: unknown): CompareFired {
  if (!isRecord(body)) throw new Error('compare-fired must be an object');
  return {
    runId: requiredString(body, 'runId'),
    queuedJobId: requiredString(body, 'queuedJobId'),
    handlerDurationMs: requiredNumber(body, 'handlerDurationMs'),
  };
}

/** Deserialize + validate the comparison ledger. */
export function comparisonPanelFromJson(body: unknown): ComparisonPanel {
  if (!isRecord(body)) throw new Error('comparison panel must be an object');
  return {
    runs: requiredArray(body, 'runs').map(comparisonRunFromJson),
    detail: requiredString(body, 'detail'),
  };
}
