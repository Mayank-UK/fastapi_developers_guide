import { describe, expect, it, vi, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ChatDemo } from './chat_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetRealtimeChatDemoUseCase } from '../../../domain/demo/get-realtime-chat-demo-usecase';
import type { ChatPanel } from '../../../domain/demo/realtime-chat';

/**
 * ChatDemo spec — fixture-driven (happy + failure) with a stubbed global
 * WebSocket: the panel renders the ceilings and the close-code table;
 * join opens a REAL WebSocket against the stubbed global (same-origin ws
 * URL with the name query), the protocol frames render (joined, roster,
 * backfill, chat with seq, notes, pongs, error frames), the send path
 * writes JSON frames, and a Failed panel degrades to the shared error
 * panel with recovery.
 */

type Stubs = {
  panel?: (room: string | null) => Promise<Result<ChatPanel>>;
};

const panel: ChatPanel = {
  policy: {
    maxRoomConnections: 8,
    perConnectionQueue: 32,
    historyCapacity: 50,
    scrollback: 10,
    roomPattern: '^[a-z0-9][a-z0-9-]{0,23}$',
    namePattern: '1-24 chars, no whitespace',
  },
  closeCodes: [
    { code: 1000, reason: 'left the room', when: 'the client disconnects cleanly' },
    { code: 1008, reason: 'unreadable frame', when: 'the stream cannot be trusted' },
    { code: 1013, reason: 'room full', when: 'reconnect soon — the ceilings' },
  ],
  rooms: [
    { room: 'demo-room', members: ['ada'], newestSeq: 2, retained: 2 },
  ],
  recentMessages: [
    { seq: 1, sender: 'ada', text: 'first', at: 1792237000 },
    { seq: 2, sender: 'ada', text: 'second', at: 1792237001 },
  ],
  stats: { messagesSent: 2, slowRetired: 0, liveConnections: 1 },
  endpoints: [{ path: '/api/realtime/chat/{room}', method: 'WS', teaches: 'join with ?name=' }],
  honestyNotes: ['rooms and history are process-local (one uvicorn worker)'],
  reasoning: 'Fanout over bounded per-connection queues.',
};

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static readonly OPEN = 1;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number; reason: string }) => void) | null = null;
  sent: string[] = [];
  lastUrl = '';

  constructor(url: string) {
    this.lastUrl = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.onclose?.({ code: 1000, reason: 'left the room' });
  }

  receive(frame: unknown): void {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }
}

function sole(index = 0): FakeWebSocket {
  const socket = FakeWebSocket.instances.at(index);
  if (!socket) throw new Error('no fake WebSocket was opened');
  return socket;
}

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetRealtimeChatDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
  } as unknown as GetRealtimeChatDemoUseCase);
}

describe('ChatDemo', () => {
  afterEach(() => {
    FakeWebSocket.instances = [];
    vi.unstubAllGlobals();
  });

  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['realtime:chat']).toBeDefined();
  });

  it('renders the ceilings and the close-code table', async () => {
    stubUseCase({});
    render(<ChatDemo />);
    await waitFor(() => expect(screen.getByTestId('realtime-chat-policy')).toBeInTheDocument());
    expect(screen.getByTestId('realtime-chat-policy')).toHaveTextContent(
      '8 members/room · queues 32',
    );
    expect(screen.getByTestId('realtime-chat-policy')).toHaveTextContent('close 1013');
  });

  it('joins through the browser WebSocket and renders the protocol frames', async () => {
    stubUseCase({});
    vi.stubGlobal('WebSocket', FakeWebSocket);
    render(<ChatDemo />);
    await waitFor(() => expect(screen.getByTestId('realtime-chat-policy')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('room id'), { target: { value: 'lobby' } });
    fireEvent.change(screen.getByLabelText('member name'), { target: { value: 'grace' } });
    screen.getByRole('button', { name: 'join' }).click();

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const socket = sole();
    expect(socket.lastUrl).toContain('/api/realtime/chat/lobby?name=grace');
    expect(socket.lastUrl).toMatch(/^ws:/);

    socket.receive({ type: 'joined', room: 'lobby', name: 'grace', gapped: false, historyWindow: 0 });
    socket.receive({ type: 'roster', members: ['ada', 'grace'] });
    socket.receive({
      type: 'backfill',
      messages: [{ seq: 7, sender: 'ada', text: 'while you were away', at: 1 }],
      gapped: false,
    });
    socket.receive({ type: 'chat', chat: { seq: 8, sender: 'ada', text: 'live line', at: 2 } });
    socket.receive({ type: 'note', text: 'ada left' });
    socket.receive({ type: 'error', code: 'unknown_type', message: 'bad frame' });

    await waitFor(() => expect(screen.getByTestId('realtime-chat-log')).toHaveTextContent('#8'));
    expect(screen.getByTestId('realtime-chat-log')).toHaveTextContent('#7 ada: while you were away');
    expect(screen.getByTestId('realtime-chat-log')).toHaveTextContent('ada: live line');
    expect(screen.getByTestId('realtime-chat-log')).toHaveTextContent('ada left');
    expect(screen.getByTestId('realtime-chat-log')).toHaveTextContent('unknown_type: bad frame');
    expect(screen.getByTestId('realtime-chat-state')).toHaveTextContent('in lobby');
    expect(screen.getByTestId('realtime-chat-state')).toHaveTextContent('ada, grace');
    expect(screen.getByTestId('realtime-chat-state')).toHaveTextContent('last seq: 8');

    // the send path writes protocol frames, the leave renders the close
    fireEvent.change(screen.getByLabelText('chat text'), { target: { value: 'hello' } });
    screen.getByRole('button', { name: 'send' }).click();
    expect(JSON.parse(socket.sent.at(0) as string)).toEqual({ type: 'chat', text: 'hello' });
    screen.getByRole('button', { name: 'ping' }).click();
    expect(JSON.parse(socket.sent.at(-1) as string)).toEqual({ type: 'ping' });
    screen.getByRole('button', { name: 'leave' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('realtime-chat-log')).toHaveTextContent('closed (1000)'),
    );
  });

  it('reconnects with ?since= the last seen seq', async () => {
    stubUseCase({});
    vi.stubGlobal('WebSocket', FakeWebSocket);
    render(<ChatDemo />);
    await waitFor(() => expect(screen.getByTestId('realtime-chat-policy')).toBeInTheDocument());
    screen.getByRole('button', { name: 'join' }).click();
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const first = sole();
    first.receive({ type: 'joined', room: 'demo-room', name: 'guest', gapped: false, historyWindow: 0 });
    first.receive({ type: 'roster', members: ['guest'] });
    first.receive({ type: 'chat', chat: { seq: 11, sender: 'ada', text: 'line', at: 3 } });
    first.close();

    const reconnect = await screen.findByRole('button', { name: 'reconnect with ?since=11' });
    expect(reconnect).toBeEnabled();
    reconnect.click();
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(2));
    expect(sole(1).lastUrl).toContain('since=11');
  });

  it('degrades to the shared error panel on a Failed panel, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Could not reach the server.', {
                code: 'unknown_error',
                status: 0,
                requestId: 'req-c1',
              }),
            )
          : success(panel);
      },
    });
    render(<ChatDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('realtime-chat-policy')).toBeInTheDocument());
  });
});
