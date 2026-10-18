import type { Result } from '../../core/result';
import type { ConsumeMode } from './msg-stream';
import type {
  ConsumeOutcome,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamPanel,
} from './msg-stream';
import type { MsgStreamRepository } from './msg-stream-repository';

/**
 * GetMsgStreamDemoUseCase — the stream lab's use case (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * Every action is repeatable — the panel always reflects the live
 * stream, so a poison read followed by reclaim shows the backlog
 * arriving and leaving for real.
 */
export class GetMsgStreamDemoUseCase {
  private readonly repository: MsgStreamRepository;

  constructor(repository: MsgStreamRepository) {
    this.repository = repository;
  }

  /** The roster: the log in id order, its length, its pending backlog. */
  panel(): Promise<Result<StreamPanel>> {
    return this.repository.panel();
  }

  /** Produce one note (XADD). */
  produce(note: string): Promise<Result<ProduceOutcome>> {
    return this.repository.produce(note);
  }

  /** Consume as the healthy or the poison persona. */
  consume(mode: ConsumeMode): Promise<Result<ConsumeOutcome>> {
    return this.repository.consume(mode);
  }

  /** The pending entries list (XPENDING). */
  pending(): Promise<Result<PendingListOutcome>> {
    return this.repository.pending();
  }

  /** Reclaim stale pending entries (XAUTOCLAIM to the healthy consumer). */
  reclaim(minIdleMs: number): Promise<Result<ReclaimOutcome>> {
    return this.repository.reclaim(minIdleMs);
  }
}
