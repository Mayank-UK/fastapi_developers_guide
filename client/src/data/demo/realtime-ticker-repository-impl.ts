import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { TickerPanel, TickerStats } from '../../domain/demo/realtime-ticker';
import type { RealtimeTickerRepository } from '../../domain/demo/realtime-ticker-repository';
import type { RealtimeTickerApi } from './realtime-ticker-api';

/**
 * RealtimeTickerRepositoryImpl — adapts the ticker API to the domain port.
 * Expected failures resolve as Failed Results; the view never sees a
 * thrown transport error.
 */
export class RealtimeTickerRepositoryImpl implements RealtimeTickerRepository {
  private readonly api: RealtimeTickerApi;

  constructor(api: RealtimeTickerApi) {
    this.api = api;
  }

  panel(): Promise<Result<TickerPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  stats(): Promise<Result<TickerStats>> {
    return safeRepositoryCall(() => this.api.stats());
  }
}
