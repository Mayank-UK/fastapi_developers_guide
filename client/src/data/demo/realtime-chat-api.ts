import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { ChatPanel } from '../../domain/demo/realtime-chat';
import { chatPanelFromJson } from './realtime-chat-dto';

/**
 * RealtimeChatApi — the transport for the chat demo's panel endpoint. The
 * live room is a browser WebSocket at this same origin (the dev proxy and
 * any production reverse proxy carry the upgrade); this class serves the
 * JSON panel around it.
 */

const PANEL_PATH = '/demo/realtime/chat';

export class RealtimeChatApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/realtime/chat[?room=…] — the panel. */
  async panel(room: string | null): Promise<ChatPanel> {
    return guardedApiCall(async () => {
      const path = room === null ? PANEL_PATH : `${PANEL_PATH}?room=${encodeURIComponent(room)}`;
      const { body, status } = await guardedGetJson(this.config, path);
      return parseDto(body, status, chatPanelFromJson);
    });
  }
}
