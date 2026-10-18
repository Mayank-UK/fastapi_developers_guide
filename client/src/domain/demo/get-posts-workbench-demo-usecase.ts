import type { Result } from '../../core/result';
import type { PostsWorkbenchRepository } from './posts-workbench-repository';
import type { WorkbenchOutcome, WorkbenchRoster, WorkbenchRound } from './posts-workbench';

/**
 * GetPostsWorkbenchDemoUseCase — drives the api-design topic's workbench
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. Failures resolve as Failed Results — the 422 a
 * refused round body earns is an outcome the component renders through
 * the shared error panel, because it IS the lesson.
 */
export class GetPostsWorkbenchDemoUseCase {
  private readonly repository: PostsWorkbenchRepository;

  constructor(repository: PostsWorkbenchRepository) {
    this.repository = repository;
  }

  roster(): Promise<Result<WorkbenchRoster>> {
    return this.repository.roster();
  }

  run(round: WorkbenchRound): Promise<Result<WorkbenchOutcome>> {
    return this.repository.run(round);
  }
}
