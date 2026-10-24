import type { Result } from '../../core/result';
import type { StatelessPanel } from './scaling-stateless';
import type { ScalingStatelessRepository } from './scaling-stateless-repository';

/**
 * GetScalingStatelessDemoUseCase — the scaling topic's live statelessness
 * panel: one read where the server introspects its own state placement —
 * the composition root's real in-process facts, a two-replica round
 * (a process-local write that never crosses, beside a real redis INCR
 * that does), and the eleven-row inventory of where every store lives.
 */
export class GetScalingStatelessDemoUseCase {
  private readonly repository: ScalingStatelessRepository;

  constructor(repository: ScalingStatelessRepository) {
    this.repository = repository;
  }

  /** The state-placement panel: two replicas, one shared counter. */
  panel(): Promise<Result<StatelessPanel>> {
    return this.repository.panel();
  }
}
