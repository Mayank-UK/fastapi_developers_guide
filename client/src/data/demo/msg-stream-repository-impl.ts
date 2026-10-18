import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type {
  ConsumeMode,
  ConsumeOutcome,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamPanel,
} from '../../domain/demo/msg-stream';
import type { MsgStreamRepository } from '../../domain/demo/msg-stream-repository';
import type { MsgStreamApi } from './msg-stream-api';

/**
 * MsgStreamRepositoryImpl — adapts the stream lab API to the domain port.
 * Every thrown transport error is guarded by safeRepositoryCall into a
 * Failed Result.
 */
export class MsgStreamRepositoryImpl implements MsgStreamRepository {
  private readonly api: MsgStreamApi;

  constructor(api: MsgStreamApi) {
    this.api = api;
  }

  panel(): Promise<Result<StreamPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  produce(note: string): Promise<Result<ProduceOutcome>> {
    return safeRepositoryCall(() => this.api.produce(note));
  }

  consume(mode: ConsumeMode): Promise<Result<ConsumeOutcome>> {
    return safeRepositoryCall(() => this.api.consume(mode));
  }

  pending(): Promise<Result<PendingListOutcome>> {
    return safeRepositoryCall(() => this.api.pending());
  }

  reclaim(minIdleMs: number): Promise<Result<ReclaimOutcome>> {
    return safeRepositoryCall(() => this.api.reclaim(minIdleMs));
  }
}
