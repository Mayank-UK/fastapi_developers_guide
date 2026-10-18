/** Domain types for the realtime chat demo (demo id `realtime:chat`). */

/** The room's ceiling facts, as the panel reports them. */
export interface ChatPolicy {
  maxRoomConnections: number;
  perConnectionQueue: number;
  historyCapacity: number;
  scrollback: number;
  roomPattern: string;
  namePattern: string;
}

/** One documented close code: number, reason, and when the server sends it. */
export interface CloseCodeRow {
  code: number;
  reason: string;
  when: string;
}

/** One live room: roster and history facts. */
export interface ChatRoomRow {
  room: string;
  members: string[];
  newestSeq: number | null;
  retained: number;
}

/** One recent chat line (the panel's transcript slice). */
export interface ChatMessageRow {
  seq: number;
  sender: string;
  text: string;
  at: number;
}

/** The chat firehose counters. */
export interface ChatStatsRow {
  messagesSent: number;
  slowRetired: number;
  liveConnections: number;
}

/** One demo endpoint the panel advertises. */
export interface ChatEndpointRow {
  path: string;
  method: string;
  teaches: string;
}

/** GET /api/demo/realtime/chat — the panel payload. */
export interface ChatPanel {
  policy: ChatPolicy;
  closeCodes: CloseCodeRow[];
  rooms: ChatRoomRow[];
  recentMessages: ChatMessageRow[];
  stats: ChatStatsRow;
  endpoints: ChatEndpointRow[];
  honestyNotes: string[];
  reasoning: string;
}

/** The wire frames the server sends over the websocket (validated shapes). */
export type ChatServerFrame =
  | { type: 'joined'; room: string; name: string; gapped: boolean; historyWindow: number }
  | { type: 'roster'; members: string[] }
  | { type: 'backfill'; messages: ChatMessageRow[]; gapped: boolean }
  | { type: 'chat'; chat: ChatMessageRow }
  | { type: 'note'; text: string }
  | { type: 'pong' }
  | { type: 'error'; code: string; message: string };

/** The wire frames the client sends over the websocket. */
export type ChatClientFrame = { type: 'chat'; text: string } | { type: 'ping' };

/** The websocket close verdict the view renders. */
export interface ChatClose {
  code: number;
  reason: string;
}
