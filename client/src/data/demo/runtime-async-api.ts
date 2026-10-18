import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import {
  runtimeAsyncDtoFromJson,
  type RuntimeAsyncDemoDto,
} from './runtime-async-dto';

/**
 * RuntimeAsyncApi — the transport for GET /api/demo/runtime/async, in the
 * same style as data/demo/runtime-types-api.ts: the request goes through
 * the shared guarded fetch pipeline (network down / non-JSON / non-2xx
 * error envelope all become typed AppExceptions), then the JSON payload is
 * validated into a DTO. Converting typed exceptions into Failed Results is
 * the repository adapter's job.
 */

const DEMO_PATH = '/demo/runtime/async';

export class RuntimeAsyncApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/runtime/async — the measured timing proof. */
  async get(): Promise<RuntimeAsyncDemoDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DEMO_PATH);
      return parseDto(body, status, runtimeAsyncDtoFromJson);
    });
  }
}
