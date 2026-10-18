import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { DataMode, EnvInspectorPanel, FailureInjection, ScenarioSnapshot } from '../../domain/demo/env-inspector';
import { envInspectorPanelFromJson, scenarioSnapshotFromJson } from './env-inspector-dto';

/**
 * EnvInspectorApi — the transport for the environments topic's inspector:
 * the panel (one honest 2xx read of the server's real configuration) and
 * the two scenario PATCHes (the flag write path). Everything rides the
 * shared guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/env';
const SCENARIO_PATH = '/demo/scenario';

export class EnvInspectorApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/env — the panel: settings, sources, flags. */
  async panel(): Promise<EnvInspectorPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, envInspectorPanelFromJson);
    });
  }

  /** PATCH /api/demo/scenario — set the data-mode flag. */
  async setDataMode(mode: DataMode): Promise<ScenarioSnapshot> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, SCENARIO_PATH, {
        method: 'PATCH',
        body: JSON.stringify({ dataMode: mode }),
      });
      return parseDto(body, status, scenarioSnapshotFromJson);
    });
  }

  /** PATCH /api/demo/scenario — set the failure-injection flag. */
  async setInjectFailure(mode: FailureInjection): Promise<ScenarioSnapshot> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, SCENARIO_PATH, {
        method: 'PATCH',
        body: JSON.stringify({ injectFailure: mode }),
      });
      return parseDto(body, status, scenarioSnapshotFromJson);
    });
  }
}
