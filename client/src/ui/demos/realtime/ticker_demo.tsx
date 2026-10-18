import { useCallback, useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { tickerTickFromJson } from '../../../data/demo/realtime-ticker-dto';
import type { TickerPanel, TickerStats, TickerTick } from '../../../domain/demo/realtime-ticker';
import { ErrorPanel } from '../../components/error-panel';

/**
 * TickerDemo — the realtime topic's SSE lab (demo id `realtime:ticker`).
 * The live stream IS the demo: the connect buttons open the browser's own
 * EventSource against the server's event stream (unbounded, or a bounded
 * five-tick run), ticks land in the log with their ids, and the firehose
 * odometer polls while the stream is open so the server's counters move
 * in step with what you see. Disconnect and reconnect to watch the
 * Last-Event-ID replay land — readyState and the last dispatched id stay
 * on the panel the whole time.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: TickerPanel };

type StreamState = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'ended';

const TICK_LOG_CAP = 30;
const STATS_POLL_MS = 2000;

const buttonClass =
  'w-fit rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50';

function stateLabel(state: StreamState): string {
  return { idle: 'not connected', connecting: 'connecting…', open: 'streaming', reconnecting: 'reconnecting…', ended: 'ended' }[state];
}

export function TickerDemo() {
  const useCase = container.getRealtimeTickerDemoUseCase;
  const apiBase = container.appConfig.apiBaseUrl;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [ticks, setTicks] = useState<TickerTick[]>([]);
  const [lastEventId, setLastEventId] = useState<string>('');
  const [streamState, setStreamState] = useState<StreamState>('idle');
  const [stats, setStats] = useState<TickerStats | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      if (result.ok) {
        setPanel({ state: 'ready', data: result.value });
      } else {
        setPanel({ state: 'failed', failure: result.failure });
      }
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  // Poll the firehose odometer while a stream is open; stop when it is not.
  useEffect(() => {
    if (streamState !== 'open' && streamState !== 'reconnecting') return;
    const timer = window.setInterval(() => {
      void useCase.stats().then((result) => {
        if (result.ok) setStats(result.value);
      });
    }, STATS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [streamState, useCase]);

  const closeStream = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  useEffect(() => closeStream, [closeStream]);

  function connect(bounded: boolean): void {
    closeStream();
    setTicks([]);
    setLastEventId('');
    const url = bounded
      ? `${apiBase}/realtime/ticker?limit=5&paceMs=400`
      : `${apiBase}/realtime/ticker`;
    const source = new EventSource(url);
    sourceRef.current = source;
    setStreamState('connecting');
    source.onopen = () => setStreamState('open');
    source.addEventListener('ready', () => setStreamState('open'));
    source.addEventListener('tick', (event) => {
      const messageEvent = event as MessageEvent<string>;
      setLastEventId(messageEvent.lastEventId);
      setTicks((previous) => [
        ...previous,
        tickerTickFromJson(JSON.parse(messageEvent.data) as unknown),
      ].slice(-TICK_LOG_CAP));
    });
    source.addEventListener('end', () => {
      source.close();
      sourceRef.current = null;
      setStreamState('ended');
    });
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        setStreamState('ended');
      } else {
        // CONNECTING: the browser is auto-reconnecting (retry hint honored) —
        // the next open frame flips the label back.
        setStreamState('reconnecting');
      }
    };
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="realtime-ticker-loading" className="text-body-sm text-on-surface-variant">
        opening the realtime ticker…
      </p>
    );
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel subject="the realtime ticker" failure={panel.failure} onRetry={refreshPanel} />
    );
  }

  const { policy } = panel.data;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="realtime-ticker-policy" className="flex flex-col gap-xxs">
        <p className="font-mono text-caption text-on-surface">
          {policy.symbols.join(' · ')} · pace {policy.defaultPaceMs}ms · retry {policy.retryMs}ms
          · ring {policy.ringCapacity} · {policy.mediaType}
        </p>
        {panel.data.honestyNotes.map((note) => (
          <p key={note} className="text-caption text-on-surface-variant">
            · {note}
          </p>
        ))}
      </section>

      <section data-testid="realtime-ticker-controls" className="flex flex-wrap gap-xs">
        <button type="button" className={buttonClass} onClick={() => connect(false)}>
          connect (unbounded)
        </button>
        <button type="button" className={buttonClass} onClick={() => connect(true)}>
          bounded run (5 ticks)
        </button>
        <button
          type="button"
          className={buttonClass}
          onClick={() => {
            closeStream();
            setStreamState('idle');
          }}
        >
          disconnect
        </button>
      </section>

      <p
        data-testid="realtime-ticker-state"
        className="font-mono text-caption text-on-surface"
      >
        stream: {stateLabel(streamState)} · last event id: {lastEventId || '(none yet)'} · ticks
        received: {ticks.length}
        {stats
          ? ` · server: ${stats.ticksSent} ticks · ${stats.clientsServed} clients · ${stats.resumeReplays} replays · ring ${stats.ringRetained}/${policy.ringCapacity}`
          : ''}
      </p>

      <div data-testid="realtime-ticker-log" className="flex flex-col gap-xxs">
        {ticks.length === 0 && (
          <p className="text-caption text-on-surface-variant">
            (no ticks yet — connect and watch them arrive)
          </p>
        )}
        {ticks.map((tick) => (
          <p key={tick.seq} className="font-mono text-caption text-on-surface">
            #{tick.seq} {tick.symbol} {tick.price.toFixed(2)}{' '}
            <span className={tick.change >= 0 ? 'text-primary' : 'text-error'}>
              {tick.change >= 0 ? '+' : ''}
              {tick.change.toFixed(2)}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
}

export default TickerDemo;
