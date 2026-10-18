import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { MethodsExchange, NoteDraft } from '../../domain/demo/reqres-methods';
import type { ReqresMethodsRepository } from '../../domain/demo/reqres-methods-repository';
import type { ReqresMethodsApi } from './reqres-methods-api';

/**
 * ReqresMethodsRepositoryImpl — adapts the notes API to the domain port.
 * Every thrown transport error (network, non-2xx envelope — including the
 * deliberate 422/404 outcomes — malformed payload) is guarded by
 * safeRepositoryCall into a Failed Result, so the demo component never
 * needs try/catch and no rejection goes unhandled.
 */
export class ReqresMethodsRepositoryImpl implements ReqresMethodsRepository {
  private readonly api: ReqresMethodsApi;

  constructor(api: ReqresMethodsApi) {
    this.api = api;
  }

  list(): Promise<Result<MethodsExchange>> {
    return safeRepositoryCall(() => this.api.list());
  }

  create(draft: NoteDraft): Promise<Result<MethodsExchange>> {
    return safeRepositoryCall(() => this.api.create(draft));
  }

  replace(id: number, draft: NoteDraft): Promise<Result<MethodsExchange>> {
    return safeRepositoryCall(() => this.api.replace(id, draft));
  }

  remove(id: number): Promise<Result<MethodsExchange>> {
    return safeRepositoryCall(() => this.api.remove(id));
  }
}
