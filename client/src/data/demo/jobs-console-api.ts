import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
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
import {
  compareFiredFromJson,
  comparisonPanelFromJson,
  deadLetterPanelFromJson,
  heartbeatFromJson,
  jobSnapshotFromJson,
  jobTicketFromJson,
  jobsPanelFromJson,
  mailboxPanelFromJson,
  queueStatsFromJson,
} from './jobs-console-dto';

/**
 * JobsConsoleApi — the transport for the jobs console's endpoints. GETs
 * and POSTs all ride the shared guarded JSON pipeline; the enqueue form
 * for the mailbox sends `to` shape-only on purpose (the worker's
 * validation decides poison — the demo's reachable no-retry path).
 */

const PANEL_PATH = '/demo/jobs/console';
const ENQUEUE_PATH = '/demo/jobs/enqueue';
const JOBS_PATH = '/demo/jobs/jobs';
const STATS_PATH = '/demo/jobs/stats';
const DLQ_PATH = '/demo/jobs/dlq';
const MAILBOX_PATH = '/demo/jobs/mailbox';
const HEARTBEAT_PATH = '/demo/jobs/heartbeat';
const COMPARE_PATH = '/demo/jobs/compare';

export class JobsConsoleApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/jobs/console — the panel (policy, catalog, tour). */
  async panel(): Promise<JobsPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, jobsPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/jobs/enqueue/{name} — enqueue a catalog task. */
  async enqueue(name: string): Promise<JobTicket> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, `${ENQUEUE_PATH}/${name}`, {
        method: 'POST',
      });
      return parseDto(body, status, jobTicketFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/jobs/jobs/{jobId} — status + attempt trail. */
  async snapshot(jobId: string): Promise<JobSnapshot> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, `${JOBS_PATH}/${jobId}`);
      return parseDto(body, status, jobSnapshotFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/jobs/stats — the two numbers. */
  async stats(): Promise<QueueStats> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, STATS_PATH);
      return parseDto(body, status, queueStatsFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/jobs/dlq — the parked jobs. */
  async deadLetters(): Promise<DeadLetterPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DLQ_PATH);
      return parseDto(body, status, deadLetterPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/jobs/dlq/{entryId}/replay — re-enqueue fresh. */
  async replay(entryId: string): Promise<JobTicket> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(
        this.config,
        `${DLQ_PATH}/${entryId}/replay`,
        { method: 'POST' },
      );
      return parseDto(body, status, jobTicketFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/jobs/mailbox — the recorded emails. */
  async mailbox(): Promise<MailboxPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, MAILBOX_PATH);
      return parseDto(body, status, mailboxPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/jobs/mailbox — compose at the boundary, defer the send. */
  async sendMail(to: string, subject: string): Promise<JobTicket> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, MAILBOX_PATH, {
        method: 'POST',
        body: JSON.stringify({ to, subject }),
      });
      return parseDto(body, status, jobTicketFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/jobs/heartbeat — the cron schedule's pulse. */
  async heartbeat(): Promise<Heartbeat> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, HEARTBEAT_PATH);
      return parseDto(body, status, heartbeatFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/jobs/compare — fire both halves of one run. */
  async compare(): Promise<CompareFired> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, COMPARE_PATH, {
        method: 'POST',
      });
      return parseDto(body, status, compareFiredFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/jobs/compare — the comparison ledger. */
  async comparison(): Promise<ComparisonPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, COMPARE_PATH);
      return parseDto(body, status, comparisonPanelFromJson);
    });
  }
}
