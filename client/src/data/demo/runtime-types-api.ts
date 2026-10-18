import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import {
  runtimeTypesDtoFromJson,
  type RuntimeTypesDemoDto,
} from './runtime-types-dto';

/**
 * RuntimeTypesApi — the transport for GET /api/demo/py/runtime-types, in
 * the same style as data/content/content-api.ts: the request goes through
 * the shared guarded fetch pipeline (network down / non-JSON / non-2xx
 * error envelope all become typed AppExceptions), then the JSON payload is
 * validated into a DTO. Converting typed exceptions into Failed Results is
 * the repository adapter's job.
 */

const DEMO_PATH = '/demo/py/runtime-types';

export class RuntimeTypesApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/py/runtime-types — the runtime-typing proof. */
  async get(): Promise<RuntimeTypesDemoDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DEMO_PATH);
      return parseDto(body, status, runtimeTypesDtoFromJson);
    });
  }
}
