import type { Result } from '../../core/result';
import type { MethodsExchange, NoteDraft } from './reqres-methods';

/**
 * ReqresMethodsRepository — the domain-facing port for the methods
 * playground demo. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 * One method per HTTP verb, mirroring the resource's contract: failures
 * (404 envelopes, 422 validation envelopes, network faults) resolve as
 * Failed Results — an exchange object exists only for 2xx answers.
 */
export interface ReqresMethodsRepository {
  /** GET the whole collection (filtered through the public model). */
  list(): Promise<Result<MethodsExchange>>;
  /** POST a full representation; 201 + Location on success. */
  create(draft: NoteDraft): Promise<Result<MethodsExchange>>;
  /** PUT a full replacement for one note; 200 on success. */
  replace(id: number, draft: NoteDraft): Promise<Result<MethodsExchange>>;
  /** DELETE one note; 204 No Content on success. */
  remove(id: number): Promise<Result<MethodsExchange>>;
}
