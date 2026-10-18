import type { Result } from '../../core/result';
import type {
  ConsumeMode,
  ConsumeOutcome,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamPanel,
} from './msg-stream';

/**
 * MsgStreamRepository — the domain-facing port for the messaging topic's
 * stream lab. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 * Five methods, one per lab action: the roster, produce, consume as a
 * persona, the pending list, and the reclaim round.
 */
export interface MsgStreamRepository {
  /** The roster panel's facts: the log in order, length, pending count. */
  panel(): Promise<Result<StreamPanel>>;
  /** Append one note (XADD); the outcome carries the minted entry id. */
  produce(note: string): Promise<Result<ProduceOutcome>>;
  /** Read as a persona; healthy acks, poison leaves entries pending. */
  consume(mode: ConsumeMode): Promise<Result<ConsumeOutcome>>;
  /** The group's pending entries list (owner, idle, deliveries). */
  pending(): Promise<Result<PendingListOutcome>>;
  /** XAUTOCLAIM stale pending entries to the healthy consumer. */
  reclaim(minIdleMs: number): Promise<Result<ReclaimOutcome>>;
}
