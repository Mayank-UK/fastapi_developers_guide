import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { InspectorProbe, RequestInspectorData } from '../../domain/demo/reqres-inspector';
import type { ReqresInspectorRepository } from '../../domain/demo/reqres-inspector-repository';
import { toReqresInspector } from './reqres-inspector-dto';
import type { ReqresInspectorApi } from './reqres-inspector-api';

/**
 * ReqresInspectorRepositoryImpl — adapts the inspector API to the domain
 * port. Every thrown transport error (network, non-2xx envelope, malformed
 * payload) is guarded by safeRepositoryCall into a Failed Result, so the
 * demo component never needs try/catch and no rejection goes unhandled.
 */
export class ReqresInspectorRepositoryImpl implements ReqresInspectorRepository {
  private readonly api: ReqresInspectorApi;

  constructor(api: ReqresInspectorApi) {
    this.api = api;
  }

  probe(request: InspectorProbe): Promise<Result<RequestInspectorData>> {
    return safeRepositoryCall(async () => toReqresInspector(await this.api.probe(request)));
  }
}
