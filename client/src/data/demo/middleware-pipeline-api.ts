import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import {
  middlewarePipelineDtoFromJson,
  type MiddlewarePipelineDto,
} from './middleware-pipeline-dto';

/**
 * MiddlewarePipelineApi — the transport for GET /api/demo/middleware/pipeline,
 * in the same style as the other data/demo adapters: a parameterless GET
 * (the demo's subject is the request itself), sent through the shared
 * guarded fetch pipeline that maps every transport failure (network down /
 * non-JSON / non-2xx envelope) to typed AppExceptions, then validated
 * into a DTO.
 */

const DEMO_PATH = '/demo/middleware/pipeline';

export class MiddlewarePipelineApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/middleware/pipeline — walk the live chain once. */
  async read(): Promise<MiddlewarePipelineDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DEMO_PATH);
      return parseDto(body, status, middlewarePipelineDtoFromJson);
    });
  }
}
