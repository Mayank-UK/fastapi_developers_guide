import type { Result } from '../../core/result';
import type { WorkbenchOutcome, WorkbenchRoster, WorkbenchRound } from './posts-workbench';

/**
 * PostsWorkbenchRepository — the domain-facing port for the api-design
 * workbench demo. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 * Two methods, one per endpoint: the roster (the substrate's live
 * facets) and the round (the traced outcome). Failures — including the
 * 422 the edge answers a combination no route matches with — resolve as
 * Failed Results.
 */
export interface PostsWorkbenchRepository {
  /** Fetch the roster: authors, tags, statuses, sorts, live totals. */
  roster(): Promise<Result<WorkbenchRoster>>;
  /** Run one round through the real posts pipeline. */
  run(round: WorkbenchRound): Promise<Result<WorkbenchOutcome>>;
}
