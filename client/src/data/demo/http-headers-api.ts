import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import {
  httpHeadersDtoFromJson,
  type HttpHeadersDemoDto,
} from './http-headers-dto';
import type { HttpHeadersDemoRequest } from '../../domain/demo/http-headers';

/**
 * HttpHeadersApi — the transport for GET/POST /api/demo/http/headers, in
 * the same style as the other data/demo adapters but through the send
 * pipeline: the demo chooses the METHOD, adds an optional custom header,
 * and (on POST) a JSON body; the shared guarded fetch pipeline maps every
 * transport failure (network down / non-JSON / non-2xx envelope) to typed
 * AppExceptions, then the JSON payload is validated into a DTO.
 *
 * The fixed `from=client-demo` query keeps the echoed raw query populated
 * and deterministic. Invalid header names must not reach fetch (it throws
 * a TypeError that would masquerade as a network failure) — the component
 * validates before sending.
 */

const DEMO_PATH = '/demo/http/headers?from=client-demo';

export class HttpHeadersApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fire the echo request as described; return what the server received. */
  async send(request: HttpHeadersDemoRequest): Promise<HttpHeadersDemoDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, DEMO_PATH, {
        method: request.method,
        headers: customHeaders(request),
        ...(request.method === 'POST'
          ? { body: JSON.stringify({ message: request.message ?? '' }) }
          : {}),
      });
      return parseDto(body, status, httpHeadersDtoFromJson);
    });
  }
}

/** The custom header pair, only when both halves are present. */
function customHeaders(request: HttpHeadersDemoRequest): Record<string, string> {
  if (request.headerName === undefined || request.headerValue === undefined) {
    return {};
  }
  return { [request.headerName]: request.headerValue };
}
