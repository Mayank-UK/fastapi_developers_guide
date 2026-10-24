import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { LogViewerPanel } from '../../domain/demo/obs-viewer';
import { logViewerPanelFromJson } from './obs-viewer-dto';

/**
 * ObsViewerApi — the transport for the observability topic's
 * structured-log viewer: one honest 2xx GET whose payload is the server's
 * real pipeline and recent-events ring. Everything rides the shared
 * guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/obs/viewer';

export class ObsViewerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/obs/viewer — the panel: pipeline, level, events. */
  async panel(): Promise<LogViewerPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, logViewerPanelFromJson);
    });
  }
}
