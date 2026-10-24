import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { DepsManifestPanel } from '../../domain/demo/dep-manifest';
import { depsManifestPanelFromJson } from './dep-manifest-dto';

/**
 * DepsManifestApi — the transport for the dependency-management topic's
 * manifest panel: one honest 2xx GET whose payload already carries its own
 * degradation (available: false) when the server could not read its
 * manifest or lock. Everything rides the shared guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/deps';

export class DepsManifestApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/deps — the panel: groups, pins, agreement, tree. */
  async panel(): Promise<DepsManifestPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, depsManifestPanelFromJson);
    });
  }
}
