import type { Result } from '../../core/result';
import type { ReqresMethodsRepository } from './reqres-methods-repository';
import type { MethodsExchange, NoteDraft } from './reqres-methods';

/**
 * ReqresMethodsDemoUseCase — drives the request-response topic's notes
 * playground (react-guide use-case style): a thin orchestration seam over
 * the repository port, one method per HTTP verb because the demo's whole
 * subject is the per-method contract. Failures resolve as Failed Results
 * — the 422 an invalid body earns and the 404 an unknown id earns are
 * outcomes the component renders, not exceptions it must catch.
 */
export class ReqresMethodsDemoUseCase {
  private readonly repository: ReqresMethodsRepository;

  constructor(repository: ReqresMethodsRepository) {
    this.repository = repository;
  }

  list(): Promise<Result<MethodsExchange>> {
    return this.repository.list();
  }

  create(draft: NoteDraft): Promise<Result<MethodsExchange>> {
    return this.repository.create(draft);
  }

  replace(id: number, draft: NoteDraft): Promise<Result<MethodsExchange>> {
    return this.repository.replace(id, draft);
  }

  remove(id: number): Promise<Result<MethodsExchange>> {
    return this.repository.remove(id);
  }
}
