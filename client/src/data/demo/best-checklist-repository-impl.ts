import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { BestChecklistPanel } from '../../domain/demo/best-checklist';
import type { BestChecklistRepository } from '../../domain/demo/best-checklist-repository';
import type { BestChecklistApi } from './best-checklist-api';

/**
 * BestChecklistRepositoryImpl — adapts the self-audit API to the domain
 * port. A Failed Result means the round itself broke (network down,
 * unparseable body); a successful panel is always the server's honest
 * audit, manuals and all.
 */
export class BestChecklistRepositoryImpl implements BestChecklistRepository {
  private readonly api: BestChecklistApi;

  constructor(api: BestChecklistApi) {
    this.api = api;
  }

  panel(): Promise<Result<BestChecklistPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
