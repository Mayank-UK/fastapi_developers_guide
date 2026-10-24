import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { ThirdPartyHubPanel } from '../../domain/demo/thirdparty-hub';
import { thirdPartyHubPanelFromJson } from './thirdparty-hub-dto';

/**
 * ThirdPartyHubApi — the transport for the third-party topic's hub
 * panel: one honest 2xx GET whose payload the server derived at request
 * time (the manifest-verified decision walk, the integration inventory,
 * the value-free secrets panel, the live quotas). Everything rides the
 * shared guarded JSON pipeline.
 */

const HUB_PATH = '/demo/thirdparty/hub';

export class ThirdPartyHubApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/thirdparty/hub — decisions, integrations, secrets, quotas. */
  async hub(): Promise<ThirdPartyHubPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, HUB_PATH, { method: 'GET' });
      return parseDto(body, status, thirdPartyHubPanelFromJson);
    });
  }
}
