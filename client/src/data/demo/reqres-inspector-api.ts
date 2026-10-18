import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { InspectorProbe } from '../../domain/demo/reqres-inspector';
import { reqresInspectorDtoFromJson, type ReqresInspectorDto } from './reqres-inspector-dto';

/**
 * ReqresInspectorApi — the transport for GET/POST
 * /api/demo/reqres/inspector, in the same style as the other data/demo
 * adapters: the probe travels exactly as the user shaped it — the query
 * string appended raw (it is the teaching subject, not a parameter to
 * encode), the optional custom header sent as-is, the optional POST body
 * carrying the message — through the shared guarded fetch pipeline that
 * maps every transport failure to typed AppExceptions, then validated
 * into a DTO.
 */

const DEMO_PATH = '/demo/reqres/inspector';

export class ReqresInspectorApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Send one probe; the server reflects the Request object's view of it. */
  async probe(probe: InspectorProbe): Promise<ReqresInspectorDto> {
    const trimmed = probe.query.trim();
    const path = `${DEMO_PATH}${trimmed === '' ? '' : `?${trimmed}`}`;
    const headers = customHeader(probe);
    const request =
      probe.method === 'POST'
        ? {
            method: 'POST' as const,
            ...(headers === undefined ? {} : { headers }),
            body: JSON.stringify(
              probe.bodyMessage === undefined ? {} : { message: probe.bodyMessage },
            ),
          }
        : { method: 'GET' as const, ...(headers === undefined ? {} : { headers }) };
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, path, request);
      return parseDto(body, status, reqresInspectorDtoFromJson);
    });
  }
}

/** The probe's optional custom header as a one-entry record, if any. */
function customHeader(probe: InspectorProbe): Record<string, string> | undefined {
  const name = probe.headerName?.trim().toLowerCase();
  if (name === undefined || name === '' || probe.headerValue === undefined) return undefined;
  return { [name]: probe.headerValue };
}
