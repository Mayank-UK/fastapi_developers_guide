import { safeRepositoryCall } from '../../core/error-handling/guards';
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
} from '../../domain/demo/jobs-console';
import type { JobsConsoleRepository } from '../../domain/demo/jobs-console-repository';
import type { JobsConsoleApi } from './jobs-console-api';

/**
 * JobsConsoleRepositoryImpl — adapts the console API to the domain port.
 * Expected failures resolve as Failed Results; the view never sees a
 * thrown transport error.
 */
export class JobsConsoleRepositoryImpl implements JobsConsoleRepository {
  private readonly api: JobsConsoleApi;

  constructor(api: JobsConsoleApi) {
    this.api = api;
  }

  panel(): Promise<Result<JobsPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  enqueue(name: string): Promise<Result<JobTicket>> {
    return safeRepositoryCall(() => this.api.enqueue(name));
  }

  snapshot(jobId: string): Promise<Result<JobSnapshot>> {
    return safeRepositoryCall(() => this.api.snapshot(jobId));
  }

  stats(): Promise<Result<QueueStats>> {
    return safeRepositoryCall(() => this.api.stats());
  }

  deadLetters(): Promise<Result<DeadLetterPanel>> {
    return safeRepositoryCall(() => this.api.deadLetters());
  }

  replay(entryId: string): Promise<Result<JobTicket>> {
    return safeRepositoryCall(() => this.api.replay(entryId));
  }

  mailbox(): Promise<Result<MailboxPanel>> {
    return safeRepositoryCall(() => this.api.mailbox());
  }

  sendMail(to: string, subject: string): Promise<Result<JobTicket>> {
    return safeRepositoryCall(() => this.api.sendMail(to, subject));
  }

  heartbeat(): Promise<Result<Heartbeat>> {
    return safeRepositoryCall(() => this.api.heartbeat());
  }

  compare(): Promise<Result<CompareFired>> {
    return safeRepositoryCall(() => this.api.compare());
  }

  comparison(): Promise<Result<ComparisonPanel>> {
    return safeRepositoryCall(() => this.api.comparison());
  }
}
