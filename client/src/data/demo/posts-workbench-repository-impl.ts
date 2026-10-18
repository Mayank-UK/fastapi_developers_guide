import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { WorkbenchOutcome, WorkbenchRoster, WorkbenchRound } from '../../domain/demo/posts-workbench';
import type { PostsWorkbenchRepository } from '../../domain/demo/posts-workbench-repository';
import type { PostsWorkbenchApi } from './posts-workbench-api';

/**
 * PostsWorkbenchRepositoryImpl — adapts the workbench API to the domain
 * port. Every thrown transport error (network, non-2xx envelope —
 * including the deliberate 422 a refused round combination earns —
 * malformed payload) is guarded by safeRepositoryCall into a Failed
 * Result, so the demo component never needs try/catch and no rejection
 * goes unhandled.
 */
export class PostsWorkbenchRepositoryImpl implements PostsWorkbenchRepository {
  private readonly api: PostsWorkbenchApi;

  constructor(api: PostsWorkbenchApi) {
    this.api = api;
  }

  roster(): Promise<Result<WorkbenchRoster>> {
    return safeRepositoryCall(() => this.api.roster());
  }

  run(round: WorkbenchRound): Promise<Result<WorkbenchOutcome>> {
    return safeRepositoryCall(() => this.api.run(round));
  }
}
