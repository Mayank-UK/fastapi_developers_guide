import type { Result } from '../../core/result';
import type { RealtimeTickerRepository } from './realtime-ticker-repository';
import type { TickerPanel, TickerStats } from './realtime-ticker';

/**
 * GetRealtimeTickerDemoUseCase — the ticker demo's use case: the panel and
 * the firehose stats over the real endpoints. Thin delegation today (the
 * demo's logic is the LIVE stream, which the view owns through the
 * browser's EventSource); the use case exists for the same reason every
 * other demo's does — the view depends on one named capability, not on an
 * HTTP client, and the stream-path constants have an obvious home here.
 */
export class GetRealtimeTickerDemoUseCase {
  private readonly repository: RealtimeTickerRepository;

  constructor(repository: RealtimeTickerRepository) {
    this.repository = repository;
  }

  /** The panel: policy, live stats, endpoint tour, honesty notes. */
  panel(): Promise<Result<TickerPanel>> {
    return this.repository.panel();
  }

  /** The firehose odometer — poll while a stream is open. */
  stats(): Promise<Result<TickerStats>> {
    return this.repository.stats();
  }
}
