import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { ChatPanel } from '../../domain/demo/realtime-chat';
import type { RealtimeChatRepository } from '../../domain/demo/realtime-chat-repository';
import type { RealtimeChatApi } from './realtime-chat-api';

/**
 * RealtimeChatRepositoryImpl — adapts the chat API to the domain port.
 * Expected failures resolve as Failed Results; the view never sees a
 * thrown transport error.
 */
export class RealtimeChatRepositoryImpl implements RealtimeChatRepository {
  private readonly api: RealtimeChatApi;

  constructor(api: RealtimeChatApi) {
    this.api = api;
  }

  panel(room: string | null): Promise<Result<ChatPanel>> {
    return safeRepositoryCall(() => this.api.panel(room));
  }
}
