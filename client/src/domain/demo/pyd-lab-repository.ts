import type { Result } from '../../core/result';
import type { PydLabReportData, PydLabSchemaData } from './pyd-lab';

/**
 * PydLabRepository — the domain-facing port for the validation-lab demo.
 * Demo components depend on this interface only; the HTTP adapter lives in
 * data/demo and is wired at the composition root.
 */
export interface PydLabRepository {
  /** Fetch the lab model's generated JSON Schema. */
  schema(): Promise<Result<PydLabSchemaData>>;
  /** Fire an edited JSON payload at the validator; get the per-field report. */
  validate(payload: unknown): Promise<Result<PydLabReportData>>;
}
