import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { ArchEventStorePanel } from '../../domain/demo/arch-eventstore';
import { archEventStorePanelFromJson } from './arch-eventstore-dto';

/**
 * ArchEventStoreApi — the transport for the advanced-architecture
 * topic's event-store panel: one honest 2xx GET whose payload the
 * server derived at request time against a REAL EventStore port
 * (append, fold, rebuild, conflict). Everything rides the shared
 * guarded JSON pipeline.
 */

const EVENTSTORE_PATH = '/demo/arch/eventstore';

export class ArchEventStoreApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/arch/eventstore — history, fold, rebuild, conflict. */
  async eventstore(): Promise<ArchEventStorePanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, EVENTSTORE_PATH, {
        method: 'GET',
      });
      return parseDto(body, status, archEventStorePanelFromJson);
    });
  }
}
