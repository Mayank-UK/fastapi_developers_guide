import type { Result } from '../../core/result';
import type {
  OutboxConsumeOutcome,
  OutboxPanel,
  OutboxWriteOutcome,
  RelayOutcome,
} from './msg-outbox';

/**
 * MsgOutboxRepository — the domain-facing port for the messaging topic's
 * outbox lab. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 * Four methods, one per lab action: the roster, the one-transaction
 * create, the relay cycle (with or without the crash window), and the
 * idempotent consume.
 */
export interface MsgOutboxRepository {
  /** The roster: table counts, recent rows, stream entries, telemetry. */
  panel(): Promise<Result<OutboxPanel>>;
  /** Create post + outbox event in ONE transaction; both or neither. */
  create(title: string, body: string): Promise<Result<OutboxWriteOutcome>>;
  /** One relay cycle; crashBeforeMark opens the publish-then-die window. */
  relay(crashBeforeMark: boolean): Promise<Result<RelayOutcome>>;
  /** The idempotent walk: processed vs skipped-duplicate counts. */
  consume(): Promise<Result<OutboxConsumeOutcome>>;
}
