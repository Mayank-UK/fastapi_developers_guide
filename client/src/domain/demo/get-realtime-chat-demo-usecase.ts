import type { Result } from '../../core/result';
import type { ChatPanel } from './realtime-chat';
import type { RealtimeChatRepository } from './realtime-chat-repository';

/**
 * GetRealtimeChatDemoUseCase — the chat demo's use case: the panel (and
 * its refresh after room activity) over the real endpoint. Thin
 * delegation today — the live room is the view's WebSocket — but the
 * view still depends on one named capability rather than an HTTP client.
 */
export class GetRealtimeChatDemoUseCase {
  private readonly repository: RealtimeChatRepository;

  constructor(repository: RealtimeChatRepository) {
    this.repository = repository;
  }

  /** The panel, optionally led by one room's roster and transcript. */
  panel(room: string | null): Promise<Result<ChatPanel>> {
    return this.repository.panel(room);
  }
}
