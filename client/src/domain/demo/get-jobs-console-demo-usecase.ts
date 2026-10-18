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
import type { JobsConsoleRepository } from './jobs-console-repository';

/**
 * GetJobsConsoleDemoUseCase — the jobs console's use case: every console
 * capability over the real endpoints. Thin delegation today (the demo's
 * logic is the LIVE queue — the enqueues, polls, replays, and the
 * comparison ARE the substrate); the use case exists for the same reason
 * every other demo's does — the view depends on one named capability,
 * not on an HTTP client, and the poll cadences have an obvious home here.
 */
export class GetJobsConsoleDemoUseCase {
  private readonly repository: JobsConsoleRepository;

  constructor(repository: JobsConsoleRepository) {
    this.repository = repository;
  }

  /** The panel: policy schedule, task catalog, endpoint tour, honesty. */
  panel(): Promise<Result<JobsPanel>> {
    return this.repository.panel();
  }

  /** Enqueue a catalog task by name. */
  enqueue(name: string): Promise<Result<JobTicket>> {
    return this.repository.enqueue(name);
  }

  /** One job's story — poll until the status is terminal. */
  snapshot(jobId: string): Promise<Result<JobSnapshot>> {
    return this.repository.snapshot(jobId);
  }

  /** The two observability numbers. */
  stats(): Promise<Result<QueueStats>> {
    return this.repository.stats();
  }

  /** The parked jobs. */
  deadLetters(): Promise<Result<DeadLetterPanel>> {
    return this.repository.deadLetters();
  }

  /** Replay a parked job fresh. */
  replay(entryId: string): Promise<Result<JobTicket>> {
    return this.repository.replay(entryId);
  }

  /** The recorded emails. */
  mailbox(): Promise<Result<MailboxPanel>> {
    return this.repository.mailbox();
  }

  /** Compose at the boundary, defer the send. */
  sendMail(to: string, subject: string): Promise<Result<JobTicket>> {
    return this.repository.sendMail(to, subject);
  }

  /** The cron heartbeat's pulse. */
  heartbeat(): Promise<Result<Heartbeat>> {
    return this.repository.heartbeat();
  }

  /** Fire both halves of one comparison run. */
  compare(): Promise<Result<CompareFired>> {
    return this.repository.compare();
  }

  /** The comparison ledger. */
  comparison(): Promise<Result<ComparisonPanel>> {
    return this.repository.comparison();
  }
}
