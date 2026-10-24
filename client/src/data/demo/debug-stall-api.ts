import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { StallPanel } from '../../domain/demo/debug-stall';
import { stallPanelFromJson } from './debug-stall-dto';

/**
 * DebugStallApi — the transport for the debugging topic's stall
 * diagnosis: one honest 2xx GET whose payload the server built by
 * running the four bounded phases with real instruments. Everything
 * rides the shared guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/debug/stall';

export class DebugStallApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/debug/stall — the diagnosis: phases, instruments, rows. */
  async panel(): Promise<StallPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, stallPanelFromJson);
    });
  }
}
