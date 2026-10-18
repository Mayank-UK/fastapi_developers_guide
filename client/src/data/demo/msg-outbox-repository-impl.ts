import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type {
  OutboxConsumeOutcome,
  OutboxPanel,
  OutboxWriteOutcome,
  RelayOutcome,
} from '../../domain/demo/msg-outbox';
import type { MsgOutboxRepository } from '../../domain/demo/msg-outbox-repository';
import type { MsgOutboxApi } from './msg-outbox-api';

/**
 * MsgOutboxRepositoryImpl — adapts the outbox lab API to the domain port.
 * Every thrown transport error is guarded by safeRepositoryCall into a
 * Failed Result.
 */
export class MsgOutboxRepositoryImpl implements MsgOutboxRepository {
  private readonly api: MsgOutboxApi;

  constructor(api: MsgOutboxApi) {
    this.api = api;
  }

  panel(): Promise<Result<OutboxPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  create(title: string, body: string): Promise<Result<OutboxWriteOutcome>> {
    return safeRepositoryCall(() => this.api.create(title, body));
  }

  relay(crashBeforeMark: boolean): Promise<Result<RelayOutcome>> {
    return safeRepositoryCall(() => this.api.relay(crashBeforeMark));
  }

  consume(): Promise<Result<OutboxConsumeOutcome>> {
    return safeRepositoryCall(() => this.api.consume());
  }
}
