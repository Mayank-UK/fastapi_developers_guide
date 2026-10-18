import type { Result } from '../../core/result';
import type { ChatPanel } from './realtime-chat';

/**
 * RealtimeChatRepository — the domain-facing port for the chat demo's JSON
 * panel (the live conversation is a browser WebSocket the view owns; this
 * port serves the rooms/ceilings/close-codes panel around it). The HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface RealtimeChatRepository {
  /** The panel: rooms, rosters, transcript, ceilings, close codes. */
  panel(room: string | null): Promise<Result<ChatPanel>>;
}
