import { useCallback, useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { chatServerFrameFromJson } from '../../../data/demo/realtime-chat-dto';
import type { ChatPanel, ChatServerFrame } from '../../../domain/demo/realtime-chat';
import { ErrorPanel } from '../../components/error-panel';

/**
 * ChatDemo — the realtime topic's websocket lab (demo id `realtime:chat`).
 * The live room IS the demo: pick a room and a name, join with the
 * browser's own WebSocket (same origin — the dev proxy carries the
 * upgrade), and watch the protocol frames land: joined, roster, chat
 * lines from other tabs, system notes, pongs, and error frames for
 * misuse. Leave, then reconnect with ?since= to watch the backfill
 * window replay what you missed; the panel above the room carries the
 * ceilings and the documented close-code table.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: ChatPanel };

/** One rendered log line: a chat message, a system note, or a verdict. */
interface LogLine {
  key: number;
  kind: 'chat' | 'note' | 'error';
  text: string;
  seq: number | null;
}

const LOG_CAP = 40;

const buttonClass =
  'w-fit rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50';
const fieldClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono text-caption text-on-surface';

let logKey = 0;
function nextLine(kind: LogLine['kind'], text: string, seq: number | null = null): LogLine {
  logKey += 1;
  return { key: logKey, kind, text, seq };
}

function socketUrl(apiBase: string, room: string, name: string, since: number | null): string {
  const path = `${apiBase}/realtime/chat/${encodeURIComponent(room)}`;
  const query = `name=${encodeURIComponent(name)}${since === null ? '' : `&since=${since}`}`;
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${window.location.host}${path}?${query}`;
}

export function ChatDemo() {
  const useCase = container.getRealtimeChatDemoUseCase;
  const apiBase = container.appConfig.apiBaseUrl;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [room, setRoom] = useState('demo-room');
  const [name, setName] = useState('guest');
  const [joined, setJoined] = useState(false);
  const [members, setMembers] = useState<string[]>([]);
  const [lastSeq, setLastSeq] = useState<number | null>(null);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [draft, setDraft] = useState('');
  const socketRef = useRef<WebSocket | null>(null);
  const joinedRef = useRef(false);

  const refreshPanel = useCallback(
    (currentRoom: string | null) => {
      void useCase.panel(currentRoom).then((result) => {
        if (result.ok) {
          setPanel({ state: 'ready', data: result.value });
        } else {
          setPanel({ state: 'failed', failure: result.failure });
        }
      });
    },
    [useCase],
  );

  useEffect(() => {
    refreshPanel(null);
  }, [refreshPanel]);

  const closeSocket = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
    joinedRef.current = false;
    setJoined(false);
    setMembers([]);
  }, []);

  useEffect(() => closeSocket, [closeSocket]);

  function handleFrame(frame: ChatServerFrame): void {
    switch (frame.type) {
      case 'joined':
        joinedRef.current = true;
        setJoined(true);
        setLines((previous) => [
          ...previous,
          nextLine(
            'note',
            `joined ${frame.room} as ${frame.name} · window ${frame.historyWindow}${frame.gapped ? ' · GAPPED' : ''}`,
          ),
        ].slice(-LOG_CAP));
        refreshPanel(frame.room);
        break;
      case 'roster':
        setMembers(frame.members);
        break;
      case 'backfill':
        setLines((previous) => [
          ...previous,
          ...frame.messages.map((message) =>
            nextLine('chat', `${message.sender}: ${message.text}`, message.seq),
          ),
          nextLine('note', `backfill ${frame.messages.length}${frame.gapped ? ' · GAPPED' : ''}`),
        ].slice(-LOG_CAP));
        break;
      case 'chat':
        setLastSeq(frame.chat.seq);
        setLines((previous) => [
          ...previous,
          nextLine('chat', `${frame.chat.sender}: ${frame.chat.text}`, frame.chat.seq),
        ].slice(-LOG_CAP));
        break;
      case 'note':
        setLines((previous) => [...previous, nextLine('note', frame.text)].slice(-LOG_CAP));
        break;
      case 'pong':
        setLines((previous) => [...previous, nextLine('note', 'pong')].slice(-LOG_CAP));
        break;
      case 'error':
        setLines((previous) => [
          ...previous,
          nextLine('error', `${frame.code}: ${frame.message}`),
        ].slice(-LOG_CAP));
        break;
    }
  }

  function join(since: number | null): void {
    closeSocket();
    setLines([]);
    const socket = new WebSocket(socketUrl(apiBase, room, name, since));
    socketRef.current = socket;
    socket.onmessage = (event: MessageEvent<string>) => {
      handleFrame(chatServerFrameFromJson(JSON.parse(event.data) as unknown));
    };
    socket.onclose = (event: CloseEvent) => {
      const wasJoined = joinedRef.current;
      joinedRef.current = false;
      setJoined(false);
      if (wasJoined || event.code === 1000) {
        setLines((previous) => [
          ...previous,
          nextLine('note', `closed (${event.code}) ${event.reason}`),
        ].slice(-LOG_CAP));
      }
      refreshPanel(room);
    };
  }

  function send(frame: string): void {
    socketRef.current?.send(frame);
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="realtime-chat-loading" className="text-body-sm text-on-surface-variant">
        opening the chat room panel…
      </p>
    );
  }
  if (panel.state === 'failed') {
    return <ErrorPanel subject="the chat room panel" failure={panel.failure} onRetry={() => refreshPanel(null)} />;
  }

  const { policy } = panel.data;
  const roomRow = panel.data.rooms.find((row) => row.room === room);

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="realtime-chat-policy" className="flex flex-col gap-xxs">
        <p className="font-mono text-caption text-on-surface">
          ceilings: {policy.maxRoomConnections} members/room · queues {policy.perConnectionQueue}
          deep · backfill window {policy.historyCapacity}
        </p>
        {panel.data.closeCodes.map((code) => (
          <p key={code.code} className="text-caption text-on-surface-variant">
            · close {code.code} — {code.when}
          </p>
        ))}
      </section>

      <section data-testid="realtime-chat-controls" className="flex flex-wrap items-center gap-xs">
        <input
          className={`${fieldClass} w-36`}
          value={room}
          onChange={(event) => setRoom(event.target.value)}
          aria-label="room id"
          disabled={joined}
        />
        <input
          className={`${fieldClass} w-28`}
          value={name}
          onChange={(event) => setName(event.target.value)}
          aria-label="member name"
          disabled={joined}
        />
        <button type="button" className={buttonClass} disabled={joined} onClick={() => join(null)}>
          join
        </button>
        <button
          type="button"
          className={buttonClass}
          disabled={joined || lastSeq === null}
          onClick={() => join(lastSeq)}
        >
          reconnect with ?since={lastSeq ?? ''}
        </button>
        <button type="button" className={buttonClass} disabled={!joined} onClick={closeSocket}>
          leave
        </button>
      </section>

      <p data-testid="realtime-chat-state" className="font-mono text-caption text-on-surface">
        {joined ? `in ${room}` : 'not connected'} · roster: {members.join(', ') || '(empty)'} · last
        seq: {lastSeq ?? '(none)'}
        {roomRow ? ` · room now: ${roomRow.members.join(', ')}` : ''}
      </p>

      <section data-testid="realtime-chat-sender" className="flex flex-wrap items-center gap-xs">
        <input
          className={`${fieldClass} min-w-48 flex-1`}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="say something (broadcasts to the room)"
          aria-label="chat text"
          disabled={!joined}
        />
        <button
          type="button"
          className={buttonClass}
          disabled={!joined || draft.trim().length === 0}
          onClick={() => {
            send(JSON.stringify({ type: 'chat', text: draft.trim() }));
            setDraft('');
          }}
        >
          send
        </button>
        <button
          type="button"
          className={buttonClass}
          disabled={!joined}
          onClick={() => send(JSON.stringify({ type: 'ping' }))}
        >
          ping
        </button>
      </section>

      <div data-testid="realtime-chat-log" className="flex flex-col gap-xxs">
        {lines.length === 0 && (
          <p className="text-caption text-on-surface-variant">
            (nothing yet — join, then open a second browser tab as someone else)
          </p>
        )}
        {lines.map((line) => (
          <p
            key={line.key}
            className={`text-caption ${line.kind === 'chat' ? 'text-on-surface' : line.kind === 'error' ? 'text-error' : 'text-on-surface-variant'}`}
          >
            {line.kind === 'chat' ? `#${line.seq} ` : ''}
            {line.text}
          </p>
        ))}
      </div>
    </div>
  );
}

export default ChatDemo;
