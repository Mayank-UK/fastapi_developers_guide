import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { DeployStackPanel } from '../../domain/demo/deploy-stack';
import { deployStackPanelFromJson } from './deploy-stack-dto';

/**
 * DeployStackApi — the transport for the deployment topic's deploy-stack
 * inspection: one honest 2xx GET whose payload the server computed at
 * request time (runtime facts, file checks, honest manuals). Everything
 * rides the shared guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/deploy/stack';

export class DeployStackApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/deploy/stack — the inspection: runtime, areas, verdicts. */
  async panel(): Promise<DeployStackPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, deployStackPanelFromJson);
    });
  }
}
