import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { BestChecklistPanel } from '../../domain/demo/best-checklist';
import { bestChecklistPanelFromJson } from './best-checklist-dto';

/**
 * BestChecklistApi — the transport for the best-practices self-audit: one
 * honest 2xx read of the server's live audit panel. Everything rides the
 * shared guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/best/checklist';

export class BestChecklistApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/best/checklist — the audit: areas, verdicts, not-does. */
  async panel(): Promise<BestChecklistPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, bestChecklistPanelFromJson);
    });
  }
}
