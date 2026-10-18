import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { PydLabReportData, PydLabSchemaData } from '../../domain/demo/pyd-lab';
import type { PydLabRepository } from '../../domain/demo/pyd-lab-repository';
import { toPydLabReport, toPydLabSchema } from './pyd-lab-dto';
import type { PydLabApi } from './pyd-lab-api';

/**
 * PydLabRepositoryImpl — adapts the validation-lab API to the domain port.
 * Every thrown transport error (network, non-2xx envelope — including the
 * 422 the server answers a refused body with — malformed payload) is
 * guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class PydLabRepositoryImpl implements PydLabRepository {
  private readonly api: PydLabApi;

  constructor(api: PydLabApi) {
    this.api = api;
  }

  schema(): Promise<Result<PydLabSchemaData>> {
    return safeRepositoryCall(async () => toPydLabSchema(await this.api.schema()));
  }

  validate(payload: unknown): Promise<Result<PydLabReportData>> {
    return safeRepositoryCall(async () => toPydLabReport(await this.api.validate(payload)));
  }
}
