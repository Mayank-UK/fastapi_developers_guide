import type { Result } from '../../core/result';
import type { BestChecklistPanel } from './best-checklist';
import type { BestChecklistRepository } from './best-checklist-repository';

/**
 * GetBestChecklistDemoUseCase — the best-practices topic's self-audit:
 * one live panel of verdicts computed by the server against the running
 * app and the repo it lives in (live probes, real file reads, honest
 * manuals), with the anti-checklist of deliberate not-does beside it.
 */
export class GetBestChecklistDemoUseCase {
  private readonly repository: BestChecklistRepository;

  constructor(repository: BestChecklistRepository) {
    this.repository = repository;
  }

  /** The audit: areas, verdicts, evidence, not-does, and the score line. */
  panel(): Promise<Result<BestChecklistPanel>> {
    return this.repository.panel();
  }
}
