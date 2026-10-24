import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { StatelessPanel } from '../../domain/demo/scaling-stateless';
import { statelessPanelFromJson } from './scaling-stateless-dto';

/**
 * ScalingStatelessApi — the transport for the scaling topic's live
 * statelessness panel: one honest 2xx GET whose payload the server
 * computed at request time (the composition root's real in-process
 * facts, the two-replica round, the state-placement inventory).
 * Everything rides the shared guarded JSON pipeline.
 */

const PANEL_PATH = '/demo/scaling/stateless';

export class ScalingStatelessApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/scaling/stateless — two replicas, one shared counter. */
  async panel(): Promise<StatelessPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, statelessPanelFromJson);
    });
  }
}
