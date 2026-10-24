import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { PerfBenchPanel } from '../../domain/demo/perf-bench';
import { perfBenchPanelFromJson } from './perf-bench-dto';

/**
 * PerfBenchApi — the transport for the performance topic's live bench:
 * one honest 2xx GET whose payload the server measured at request time
 * (real compression bytes and timings, the hygiene comparison, loop/
 * pool/GC introspection). Everything rides the shared guarded JSON
 * pipeline.
 */

const PANEL_PATH = '/demo/perf/bench';

export class PerfBenchApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/perf/bench — the bench: measured rows, never asserted ones. */
  async panel(): Promise<PerfBenchPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, perfBenchPanelFromJson);
    });
  }
}
