import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { ArchSagaPanel } from '../../domain/demo/arch-saga';
import { archSagaPanelFromJson } from './arch-saga-dto';

/**
 * ArchSagaApi — the transport for the advanced-architecture topic's
 * saga panel: one honest 2xx GET whose payload the server derived at
 * request time by driving the REAL SagaCoordinator through a committed
 * run and a compensated one. Everything rides the shared guarded JSON
 * pipeline.
 */

const SAGA_PATH = '/demo/arch/saga';

export class ArchSagaApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/arch/saga — workflow, both runs, the proofs. */
  async saga(): Promise<ArchSagaPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, SAGA_PATH, { method: 'GET' });
      return parseDto(body, status, archSagaPanelFromJson);
    });
  }
}
