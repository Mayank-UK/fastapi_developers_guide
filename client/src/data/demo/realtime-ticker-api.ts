import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { TickerPanel, TickerStats } from '../../domain/demo/realtime-ticker';
import { tickerPanelFromJson, tickerStatsFromJson } from './realtime-ticker-dto';

/**
 * RealtimeTickerApi — the transport for the ticker demo's two JSON
 * endpoints. Both ride the shared guarded JSON pipeline; the EVENT STREAM
 * itself is not fetched through here — the view opens it with the
 * browser's EventSource at this same origin-relative path, so the dev
 * proxy (and any production reverse proxy) carries it.
 */

const PANEL_PATH = '/demo/realtime/ticker';
const STATS_PATH = '/demo/realtime/ticker/stats';

export class RealtimeTickerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/realtime/ticker — the panel (policy, tour). */
  async panel(): Promise<TickerPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, tickerPanelFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/realtime/ticker/stats — the firehose odometer. */
  async stats(): Promise<TickerStats> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, STATS_PATH);
      return parseDto(body, status, tickerStatsFromJson);
    });
  }
}
