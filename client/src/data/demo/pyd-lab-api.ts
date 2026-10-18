import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import { pydLabReportDtoFromJson, pydLabSchemaDtoFromJson, type PydLabReportDto, type PydLabSchemaDto } from './pyd-lab-dto';

/**
 * PydLabApi — the transport for the validation lab: GET
 * /api/demo/pyd/lab/schema and POST /api/demo/pyd/lab/validate, through
 * the shared guarded fetch pipelines. The payload is submitted VERBATIM
 * (the user's edited JSON), with an explicit JSON content-type — the
 * server's pydantic boundary parses by that contract, and a body sent as
 * fetch's default text/plain is refused before the lab ever runs.
 */

const SCHEMA_PATH = '/demo/pyd/lab/schema';
const VALIDATE_PATH = '/demo/pyd/lab/validate';

export class PydLabApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the lab model's generated JSON Schema. */
  async schema(): Promise<PydLabSchemaDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, SCHEMA_PATH);
      return parseDto(body, status, pydLabSchemaDtoFromJson);
    });
  }

  /** Submit an edited JSON payload; return the per-field validation report. */
  async validate(payload: unknown): Promise<PydLabReportDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, VALIDATE_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return parseDto(body, status, pydLabReportDtoFromJson);
    });
  }
}
