import type { Result } from '../../core/result';
import type { HttpHeadersDemoRequest, HttpHeadersEchoData } from './http-headers';

/**
 * HttpHeadersRepository — the domain-facing port for the headers-echo demo.
 * Demo components depend on this interface only; the HTTP adapter lives in
 * data/demo and is wired at the composition root.
 */
export interface HttpHeadersRepository {
  /** Fire the echo request as described; get back what the server received. */
  send(request: HttpHeadersDemoRequest): Promise<Result<HttpHeadersEchoData>>;
}
