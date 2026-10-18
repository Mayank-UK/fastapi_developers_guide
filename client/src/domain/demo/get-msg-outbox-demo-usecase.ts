import type { Result } from '../../core/result';
import type {
  OutboxConsumeOutcome,
  OutboxPanel,
  OutboxWriteOutcome,
  RelayOutcome,
} from './msg-outbox';
import type { MsgOutboxRepository } from './msg-outbox-repository';

/**
 * GetMsgOutboxDemoUseCase — the outbox lab's use case (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * The crash round followed by a normal round and a consume is the
 * demo's whole proof — the counts refresh from the real stores.
 */
export class GetMsgOutboxDemoUseCase {
  private readonly repository: MsgOutboxRepository;

  constructor(repository: MsgOutboxRepository) {
    this.repository = repository;
  }

  /** The roster: table counts, recent rows, the stream, telemetry. */
  panel(): Promise<Result<OutboxPanel>> {
    return this.repository.panel();
  }

  /** The one-transaction dual write: a post and its event, together. */
  create(title: string, body: string): Promise<Result<OutboxWriteOutcome>> {
    return this.repository.create(title, body);
  }

  /** One relay cycle, with or without the simulated crash window. */
  relay(crashBeforeMark: boolean): Promise<Result<RelayOutcome>> {
    return this.repository.relay(crashBeforeMark);
  }

  /** The idempotent walk over the outbox stream. */
  consume(): Promise<Result<OutboxConsumeOutcome>> {
    return this.repository.consume();
  }
}
