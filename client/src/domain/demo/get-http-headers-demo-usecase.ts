import type { Result } from '../../core/result';
import type { HttpHeadersRepository } from './http-headers-repository';
import type { HttpHeadersDemoRequest, HttpHeadersEchoData } from './http-headers';

/**
 * GetHttpHeadersDemoUseCase — fires the http-web topic's headers-echo
 * request (react-guide use-case style): a thin orchestration seam over the
 * repository port. Carries the request parameters because this demo is
 * interactive — the user chooses method, optional custom header, and
 * optional message; the server echoes what actually arrived.
 */
export class GetHttpHeadersDemoUseCase {
  private readonly repository: HttpHeadersRepository;

  constructor(repository: HttpHeadersRepository) {
    this.repository = repository;
  }

  execute(request: HttpHeadersDemoRequest): Promise<Result<HttpHeadersEchoData>> {
    return this.repository.send(request);
  }
}
