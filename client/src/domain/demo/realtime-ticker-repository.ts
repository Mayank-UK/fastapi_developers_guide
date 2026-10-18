import type { Result } from '../../core/result';
import type { TickerPanel, TickerStats } from './realtime-ticker';

/**
 * RealtimeTickerRepository — the domain-facing port for the ticker demo's
 * two JSON endpoints (the event stream itself is a browser EventSource,
 * not an HTTP round-trip this port could own). Demo components depend on
 * this interface only; the HTTP adapter lives in data/demo and is wired
 * at the composition root.
 */
export interface RealtimeTickerRepository {
  /** The panel: policy, live stats, endpoint tour, honesty notes. */
  panel(): Promise<Result<TickerPanel>>;
  /** The firehose odometer, polled while a stream is open. */
  stats(): Promise<Result<TickerStats>>;
}
