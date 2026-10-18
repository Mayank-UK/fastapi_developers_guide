import type { Result } from '../../core/result';
import type { InspectorProbe, RequestInspectorData } from './reqres-inspector';

/**
 * ReqresInspectorRepository — the domain-facing port for the request
 * inspector demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface ReqresInspectorRepository {
  /** Send one probe and reflect the server's view of it. */
  probe(request: InspectorProbe): Promise<Result<RequestInspectorData>>;
}
