import type { Result } from '../../core/result';
import type { GuardCredential, AuthzMatrixRepository } from './authz-matrix-repository';
import type {
  AuthzCheckOutcome,
  AuthzPanel,
  EditedPostOutcome,
  ModeratedCommentOutcome,
  ResourceKind,
} from './authz-matrix';

/**
 * GetAuthzMatrixDemoUseCase — the matrix lab's use case: the panel, the
 * what-if check over the real engine, and the two genuinely guarded
 * endpoints (edit post, moderate comment) whose 200s carry the allowing
 * reason and whose 403s surface as Failures carrying the deny reason.
 */
export class GetAuthzMatrixDemoUseCase {
  private readonly repository: AuthzMatrixRepository;

  constructor(repository: AuthzMatrixRepository) {
    this.repository = repository;
  }

  /** The panel: principals, matrix, targets, and the pinned notes. */
  panel(): Promise<Result<AuthzPanel>> {
    return this.repository.panel();
  }

  /** The what-if check: the engine's verdict with its reason. */
  check(
    principalName: string,
    action: string,
    scopes: string[] | null,
    resourceKind: ResourceKind | null,
    resourceId: string | null,
  ): Promise<Result<AuthzCheckOutcome>> {
    return this.repository.check(principalName, action, scopes, resourceKind, resourceId);
  }

  /** The guarded edit (owner-or-authority) — 200 or the 403 envelope. */
  editPost(credential: GuardCredential, postId: string): Promise<Result<EditedPostOutcome>> {
    return this.repository.editPost(credential, postId);
  }

  /** The guarded moderation (admin-only) — 200 or the 403 envelope. */
  moderateComment(
    credential: GuardCredential,
    commentId: string,
    status: 'visible' | 'hidden',
  ): Promise<Result<ModeratedCommentOutcome>> {
    return this.repository.moderateComment(credential, commentId, status);
  }
}
