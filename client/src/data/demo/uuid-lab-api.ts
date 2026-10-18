import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { UuidLab } from '../../domain/demo/uuid-lab';
import { uuidLabFromJson } from './uuid-lab-dto';

/**
 * UuidLabApi — the transport for GET /api/demo/db/uuid: the freshly
 * minted uuid4/UUIDv7/sequence comparison through the shared guarded
 * fetch pipeline. Transport failures (network down, non-JSON, non-2xx
 * envelope) become typed AppExceptions; a good transport is validated
 * into the DTO. The lab needs no parameters — the server mints every
 * run at request time.
 */

const LAB_PATH = '/demo/db/uuid';

export class UuidLabApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/uuid — the id-strategy comparison, minted live. */
  async lab(): Promise<UuidLab> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, LAB_PATH);
      return parseDto(body, status, uuidLabFromJson);
    });
  }
}
