import type {
  ChatEndpointRow,
  ChatMessageRow,
  ChatPanel,
  ChatRoomRow,
  ChatServerFrame,
  CloseCodeRow,
} from '../../domain/demo/realtime-chat';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * RealtimeChatDTO — the wire/transport shapes of the chat demo's panel and
 * the websocket frames, validated field-by-field so a shape violation
 * surfaces as a typed failure instead of "[object Object]" reaching the
 * UI. `newestSeq` is the only null on the panel wire (an empty history);
 * unknown server frame types degrade to a note-shaped row rather than
 * crashing the log.
 */

function messageFromJson(value: unknown): ChatMessageRow {
  if (!isRecord(value)) throw new Error('chat message must be an object');
  return {
    seq: requiredNumber(value, 'seq'),
    sender: requiredString(value, 'sender'),
    text: requiredString(value, 'text'),
    at: requiredNumber(value, 'at'),
  };
}

function roomFromJson(value: unknown): ChatRoomRow {
  if (!isRecord(value)) throw new Error('chat room row must be an object');
  const newestSeq = value['newestSeq'];
  if (newestSeq !== null && typeof newestSeq !== 'number') {
    throw new Error('newestSeq must be a number or null');
  }
  return {
    room: requiredString(value, 'room'),
    members: requiredArray(value, 'members').map((member) => {
      if (typeof member !== 'string') throw new Error('room members must be strings');
      return member;
    }),
    newestSeq,
    retained: requiredNumber(value, 'retained'),
  };
}

function closeCodeFromJson(value: unknown): CloseCodeRow {
  if (!isRecord(value)) throw new Error('close code row must be an object');
  return {
    code: requiredNumber(value, 'code'),
    reason: requiredString(value, 'reason'),
    when: requiredString(value, 'when'),
  };
}

function endpointFromJson(value: unknown): ChatEndpointRow {
  if (!isRecord(value)) throw new Error('chat endpoint row must be an object');
  return {
    path: requiredString(value, 'path'),
    method: requiredString(value, 'method'),
    teaches: requiredString(value, 'teaches'),
  };
}

/** Deserialize + validate the chat panel. */
export function chatPanelFromJson(body: unknown): ChatPanel {
  if (!isRecord(body)) throw new Error('chat panel must be an object');
  const policy = body['policy'];
  if (!isRecord(policy)) throw new Error('policy must be an object');
  const stats = body['stats'];
  if (!isRecord(stats)) throw new Error('stats must be an object');
  const honestyNotes = requiredArray(body, 'honestyNotes').map((note) => {
    if (typeof note !== 'string') throw new Error('honesty notes must be strings');
    return note;
  });
  return {
    policy: {
      maxRoomConnections: requiredNumber(policy, 'maxRoomConnections'),
      perConnectionQueue: requiredNumber(policy, 'perConnectionQueue'),
      historyCapacity: requiredNumber(policy, 'historyCapacity'),
      scrollback: requiredNumber(policy, 'scrollback'),
      roomPattern: requiredString(policy, 'roomPattern'),
      namePattern: requiredString(policy, 'namePattern'),
    },
    closeCodes: requiredArray(body, 'closeCodes').map(closeCodeFromJson),
    rooms: requiredArray(body, 'rooms').map(roomFromJson),
    recentMessages: requiredArray(body, 'recentMessages').map(messageFromJson),
    stats: {
      messagesSent: requiredNumber(stats, 'messagesSent'),
      slowRetired: requiredNumber(stats, 'slowRetired'),
      liveConnections: requiredNumber(stats, 'liveConnections'),
    },
    endpoints: requiredArray(body, 'endpoints').map(endpointFromJson),
    honestyNotes,
    reasoning: requiredString(body, 'reasoning'),
  };
}

/**
 * Parse one websocket message into a typed server frame. Unknown frame
 * types (the protocol may grow) render as a note instead of throwing —
 * the tolerant-reader stance, mirrored client-side.
 */
export function chatServerFrameFromJson(body: unknown): ChatServerFrame {
  if (!isRecord(body)) throw new Error('chat frame must be an object');
  const type = requiredString(body, 'type');
  switch (type) {
    case 'joined':
      return {
        type: 'joined',
        room: requiredString(body, 'room'),
        name: requiredString(body, 'name'),
        gapped: requiredBoolean(body, 'gapped'),
        historyWindow: requiredNumber(body, 'historyWindow'),
      };
    case 'roster':
      return {
        type: 'roster',
        members: requiredArray(body, 'members').map((member) => {
          if (typeof member !== 'string') throw new Error('roster members must be strings');
          return member;
        }),
      };
    case 'backfill':
      return {
        type: 'backfill',
        messages: requiredArray(body, 'messages').map(messageFromJson),
        gapped: requiredBoolean(body, 'gapped'),
      };
    case 'chat': {
      const chat = body['chat'];
      if (!isRecord(chat)) throw new Error('chat frame payload must be an object');
      return { type: 'chat', chat: messageFromJson(chat) };
    }
    case 'note':
      return { type: 'note', text: requiredString(body, 'text') };
    case 'pong':
      return { type: 'pong' };
    case 'error':
      return {
        type: 'error',
        code: requiredString(body, 'code'),
        message: requiredString(body, 'message'),
      };
    default:
      return { type: 'note', text: `(unknown frame type ${type})` };
  }
}
