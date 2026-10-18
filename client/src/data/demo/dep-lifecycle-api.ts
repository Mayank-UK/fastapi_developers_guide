import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import {
  depLifecycleLogDtoFromJson,
  depLifecycleSpanDtoFromJson,
  type DepLifecycleLogDto,
  type DepLifecycleSpanDto,
} from './dep-lifecycle-dto';

/**
 * DepLifecycleApi — the transport for the yield-dependency demo: GET
 * /api/demo/dep/lifecycle (fire a wrapped request) and GET
 * /api/demo/dep/lifecycle/log (the shared span ring), through the shared
 * guarded fetch pipelines.
 */

const FIRE_PATH = '/demo/dep/lifecycle';
const LOG_PATH = '/demo/dep/lifecycle/log';

export class DepLifecycleApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fire one wrapped request; get the span facts the handler can know. */
  async fire(): Promise<DepLifecycleSpanDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, FIRE_PATH);
      return parseDto(body, status, depLifecycleSpanDtoFromJson);
    });
  }

  /** Read the shared span log — the ordering proof, as data. */
  async log(): Promise<DepLifecycleLogDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, LOG_PATH);
      return parseDto(body, status, depLifecycleLogDtoFromJson);
    });
  }
}
