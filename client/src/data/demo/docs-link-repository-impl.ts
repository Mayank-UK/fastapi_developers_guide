import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { DocsHub } from '../../domain/demo/docs-link';
import type { DocsLinkRepository } from '../../domain/demo/docs-link-repository';
import type { DocsLinkApi } from './docs-link-api';

/**
 * DocsLinkRepositoryImpl — adapts the hub API to the domain port. Every
 * thrown transport error (network, non-2xx envelope, malformed payload)
 * is guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class DocsLinkRepositoryImpl implements DocsLinkRepository {
  private readonly api: DocsLinkApi;

  constructor(api: DocsLinkApi) {
    this.api = api;
  }

  hub(): Promise<Result<DocsHub>> {
    return safeRepositoryCall(() => this.api.hub());
  }
}
