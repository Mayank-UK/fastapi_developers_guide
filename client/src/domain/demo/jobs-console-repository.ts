import type { Result } from '../../core/result';
import type {
  CompareFired,
  ComparisonPanel,
  DeadLetterPanel,
  Heartbeat,
  JobSnapshot,
  JobTicket,
  JobsPanel,
  MailboxPanel,
  QueueStats,
} from './jobs-console';

/**
 * JobsConsoleRepository — the domain-facing port for the jobs console's
 * endpoints. Demo components depend on this interface only; the HTTP adapter
 * lives in data/demo and is wired at the composition root. The enqueue form
 * for the mailbox keeps `to` deliberately shape-only: the WORKER's validation
 * decides poison, which is the demo's reachable no-retry path.
 */
export interface JobsConsoleRepository {
  /** The panel: policy schedule, task catalog, endpoint tour, honesty. */
  panel(): Promise<Result<JobsPanel>>;
  /** Enqueue a catalog task by name — the worker's name table decides. */
  enqueue(name: string): Promise<Result<JobTicket>>;
  /** One job's story: status, attempt trail, verdict. */
  snapshot(jobId: string): Promise<Result<JobSnapshot>>;
  /** The two observability numbers, live from the queue's zset. */
  stats(): Promise<Result<QueueStats>>;
  /** The parked jobs, newest first. */
  deadLetters(): Promise<Result<DeadLetterPanel>>;
  /** Replay a parked job fresh — new id, attempts reset, entry kept. */
  replay(entryId: string): Promise<Result<JobTicket>>;
  /** The recorded emails. */
  mailbox(): Promise<Result<MailboxPanel>>;
  /** Compose at the boundary and defer the send (the email-as-job flow). */
  sendMail(to: string, subject: string): Promise<Result<JobTicket>>;
  /** The cron schedule's pulse. */
  heartbeat(): Promise<Result<Heartbeat>>;
  /** Fire both halves of one comparison run (in-process + queued). */
  compare(): Promise<Result<CompareFired>>;
  /** The comparison ledger, newest first. */
  comparison(): Promise<Result<ComparisonPanel>>;
}
