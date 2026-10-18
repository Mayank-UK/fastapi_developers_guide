import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import { depMatrixDtoFromJson, type DepMatrixDto } from './dep-matrix-dto';

/**
 * DepMatrixApi — the transport for the dependency matrix: GET
 * /api/demo/dep/matrix through the shared guarded fetch pipeline. One
 * request resolves every flavor server-side; the identity proofs arrive
 * as rows.
 */

const MATRIX_PATH = '/demo/dep/matrix';

export class DepMatrixApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Resolve the whole dependency matrix in one request. */
  async matrix(): Promise<DepMatrixDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, MATRIX_PATH);
      return parseDto(body, status, depMatrixDtoFromJson);
    });
  }
}
