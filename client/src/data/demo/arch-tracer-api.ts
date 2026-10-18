import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import { archTracerDtoFromJson, type ArchTracerDto } from './arch-tracer-dto';

/**
 * ArchTracerApi — the transport for GET /api/demo/arch/tracer, in the
 * same style as the other data/demo adapters: a parameterless GET (the
 * demo's subject is the running app itself), sent through the shared
 * guarded fetch pipeline that maps every transport failure (network down /
 * non-JSON / non-2xx envelope) to typed AppExceptions, then validated
 * into a DTO.
 */

const DEMO_PATH = '/demo/arch/tracer';

export class ArchTracerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/arch/tracer — introspect + trace once. */
  async read(): Promise<ArchTracerDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DEMO_PATH);
      return parseDto(body, status, archTracerDtoFromJson);
    });
  }
}
