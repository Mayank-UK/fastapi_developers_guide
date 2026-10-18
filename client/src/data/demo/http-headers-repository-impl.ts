import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type {
  HttpHeadersDemoRequest,
  HttpHeadersEchoData,
} from '../../domain/demo/http-headers';
import type { HttpHeadersRepository } from '../../domain/demo/http-headers-repository';
import { toHttpHeadersEcho } from './http-headers-dto';
import type { HttpHeadersApi } from './http-headers-api';

/**
 * HttpHeadersRepositoryImpl — adapts the headers-echo API to the domain
 * port. Every thrown transport error (network, non-2xx, malformed payload)
 * is guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class HttpHeadersRepositoryImpl implements HttpHeadersRepository {
  private readonly api: HttpHeadersApi;

  constructor(api: HttpHeadersApi) {
    this.api = api;
  }

  send(request: HttpHeadersDemoRequest): Promise<Result<HttpHeadersEchoData>> {
    return safeRepositoryCall(async () => toHttpHeadersEcho(await this.api.send(request)));
  }
}
