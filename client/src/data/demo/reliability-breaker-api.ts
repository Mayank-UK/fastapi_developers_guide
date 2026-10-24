import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { BreakerPanel } from '../../domain/demo/reliability-breaker';
import { breakerPanelFromJson } from './reliability-breaker-dto';

/**
 * ReliabilityBreakerApi — the transport for the reliability topic's live
 * circuit breaker: one honest 2xx GET whose payload the server computed
 * at request time (the full-cycle walk over the real pure substrate,
 * every verdict and latency real). Everything rides the shared guarded
 * JSON pipeline.
 */

const PANEL_PATH = '/demo/reliability/breaker';

export class ReliabilityBreakerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/reliability/breaker — the breaker: closed → open → half-open → closed. */
  async panel(): Promise<BreakerPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, breakerPanelFromJson);
    });
  }
}
