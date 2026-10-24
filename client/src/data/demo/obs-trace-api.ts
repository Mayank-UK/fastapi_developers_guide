import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { TraceFanout } from '../../domain/demo/obs-trace';
import { traceFanoutFromJson } from './obs-trace-dto';

/**
 * ObsTraceApi — the transport for the observability topic's trace fan-out:
 * one honest 2xx GET whose payload the server built by driving three REAL
 * internal requests through the running app. Everything rides the shared
 * guarded JSON pipeline.
 */

const FANOUT_PATH = '/demo/obs/trace';

export class ObsTraceApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/obs/trace — the fan-out: root, rounds, correlation. */
  async fanout(): Promise<TraceFanout> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, FANOUT_PATH, { method: 'GET' });
      return parseDto(body, status, traceFanoutFromJson);
    });
  }
}
