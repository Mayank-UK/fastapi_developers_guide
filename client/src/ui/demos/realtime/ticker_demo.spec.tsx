import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TickerDemo } from './ticker_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetRealtimeTickerDemoUseCase } from '../../../domain/demo/get-realtime-ticker-demo-usecase';
import type { TickerPanel, TickerStats, TickerTick } from '../../../domain/demo/realtime-ticker';

/**
 * TickerDemo spec — fixture-driven (happy + failure) with a stubbed global
 * EventSource: the panel renders the policy and honesty notes; the bounded
 * run opens a REAL EventSource against the stubbed global and renders the
 * dispatched ready/tick/end events (ids, log, connection label); the
 * onerror window labels the browser's auto-reconnect; a Failed panel
 * degrades to the shared error panel with recovery.
 */

type Stubs = {
  panel?: () => Promise<Result<TickerPanel>>;
  stats?: () => Promise<Result<TickerStats>>;
};

type Listener = (event: { type: string; data?: string; lastEventId?: string }) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = FakeEventSource.CONNECTING;
  lastUrl = '';
  private readonly listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.lastUrl = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    this.readyState = FakeEventSource.CLOSED;
  }

  dispatch(type: string, data?: string, lastEventId?: string): void {
    for (const listener of this.listeners.get(type) ?? []) listener({ type, data, lastEventId });
  }
}

function emptyStats(): TickerStats {
  return {
    ticksSent: 0,
    clientsServed: 0,
    resumeReplays: 0,
    ringRetained: 0,
    oldestSeq: null,
    newestSeq: null,
  };
}

const panel: TickerPanel = {
  policy: {
    symbols: ['FDG', 'ASY', 'PYC'],
    defaultPaceMs: 750,
    retryMs: 3000,
    keepaliveEvery: 4,
    ringCapacity: 120,
    mediaType: 'text/event-stream',
  },
  stats: emptyStats(),
  endpoints: [{ path: '/api/realtime/ticker', method: 'GET', teaches: 'the live event stream' }],
  honestyNotes: ['pacing is a simulated server-side sleep over a deterministic price walk'],
  reasoning: 'One shared market, one replayable ring.',
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetRealtimeTickerDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    stats:
      stubs.stats ?? (async () => success({ ...emptyStats(), ticksSent: 2, clientsServed: 1 })),
  } as unknown as GetRealtimeTickerDemoUseCase);
}

function sole(): FakeEventSource {
  const source = FakeEventSource.instances.at(0);
  if (!source) throw new Error('no fake EventSource was opened');
  return source;
}

function tick(seq: number): TickerTick {
  return { seq, symbol: 'FDG', price: 128 + seq, change: 0.25, at: 1792237000 + seq };
}

describe('TickerDemo', () => {
  afterEach(() => {
    FakeEventSource.instances = [];
    vi.unstubAllGlobals();
  });

  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['realtime:ticker']).toBeDefined();
  });

  it('renders the policy and the honesty notes', async () => {
    stubUseCase({});
    render(<TickerDemo />);
    await waitFor(() => expect(screen.getByTestId('realtime-ticker-policy')).toBeInTheDocument());
    expect(screen.getByTestId('realtime-ticker-policy')).toHaveTextContent('FDG · ASY · PYC');
    expect(screen.getByTestId('realtime-ticker-policy')).toHaveTextContent('text/event-stream');
    expect(screen.getByTestId('realtime-ticker-policy')).toHaveTextContent('simulated');
  });

  it('streams through the browser EventSource and renders ticks with ids', async () => {
    stubUseCase({});
    vi.stubGlobal('EventSource', FakeEventSource);
    render(<TickerDemo />);
    await waitFor(() => expect(screen.getByTestId('realtime-ticker-policy')).toBeInTheDocument());

    screen.getByRole('button', { name: 'bounded run (5 ticks)' }).click();
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const source = sole();
    expect(source.lastUrl).toContain('/api/realtime/ticker?limit=5');

    source.readyState = FakeEventSource.OPEN;
    source.onopen?.();
    source.dispatch('ready');
    source.dispatch('tick', JSON.stringify(tick(4)), '4');
    source.dispatch('tick', JSON.stringify(tick(5)), '5');

    await waitFor(() => expect(screen.getByTestId('realtime-ticker-log')).toHaveTextContent('#4'));
    expect(screen.getByTestId('realtime-ticker-log')).toHaveTextContent('#5 FDG 133.00');
    expect(screen.getByTestId('realtime-ticker-state')).toHaveTextContent('streaming');
    expect(screen.getByTestId('realtime-ticker-state')).toHaveTextContent('last event id: 5');

    source.dispatch('end', '{"reason":"limit"}');
    await waitFor(() =>
      expect(screen.getByTestId('realtime-ticker-state')).toHaveTextContent('ended'),
    );
    expect(source.readyState).toBe(FakeEventSource.CLOSED);
  });

  it('labels the auto-reconnect window from onerror', async () => {
    stubUseCase({});
    vi.stubGlobal('EventSource', FakeEventSource);
    render(<TickerDemo />);
    await waitFor(() => expect(screen.getByTestId('realtime-ticker-policy')).toBeInTheDocument());
    screen.getByRole('button', { name: 'connect (unbounded)' }).click();
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const source = sole();

    source.readyState = FakeEventSource.OPEN;
    source.onopen?.();
    source.readyState = FakeEventSource.CONNECTING; // the browser is retrying
    source.onerror?.();
    await waitFor(() =>
      expect(screen.getByTestId('realtime-ticker-state')).toHaveTextContent('reconnecting'),
    );
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
                requestId: 'req-t1',
              }),
            )
          : success(panel);
      },
    });
    render(<TickerDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('realtime-ticker-policy')).toBeInTheDocument());
  });
});
