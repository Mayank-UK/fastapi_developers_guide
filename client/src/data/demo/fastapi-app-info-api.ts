import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import {
  fastApiAppInfoDtoFromJson,
  type FastApiAppInfoDto,
} from './fastapi-app-info-dto';

/**
 * FastApiAppInfoApi — the transport for GET /api/demo/fastapi/app-info, in
 * the same style as the other data/demo adapters: the request goes through
 * the shared guarded fetch pipeline (network down / non-JSON / non-2xx
 * error envelope all become typed AppExceptions), then the JSON payload is
 * validated into a DTO. Converting typed exceptions into Failed Results is
 * the repository adapter's job.
 */

const DEMO_PATH = '/demo/fastapi/app-info';

export class FastApiAppInfoApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/fastapi/app-info — the app, introduced by itself. */
  async get(): Promise<FastApiAppInfoDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DEMO_PATH);
      return parseDto(body, status, fastApiAppInfoDtoFromJson);
    });
  }
}
