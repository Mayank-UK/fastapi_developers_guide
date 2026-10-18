import type { Result } from '../../core/result';
import type { ReqresInspectorRepository } from './reqres-inspector-repository';
import type { InspectorProbe, RequestInspectorData } from './reqres-inspector';

/**
 * GetReqresInspectorDemoUseCase — sends the request-response topic's
 * probe (react-guide use-case style): a thin orchestration seam over the
 * repository port. Carries the probe because this demo is interactive —
 * the user shapes the request (query, custom header, optional POST body)
 * and the server reflects the live Request object's view of exactly that
 * request.
 */
export class GetReqresInspectorDemoUseCase {
  private readonly repository: ReqresInspectorRepository;

  constructor(repository: ReqresInspectorRepository) {
    this.repository = repository;
  }

  execute(probe: InspectorProbe): Promise<Result<RequestInspectorData>> {
    return this.repository.probe(probe);
  }
}
