import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  AuthzCheckOutcome,
  AuthzPanel,
  EditedPostOutcome,
  ModeratedCommentOutcome,
  ResourceKind,
} from '../../domain/demo/authz-matrix';
import type { GuardCredential, AuthzMatrixRepository } from '../../domain/demo/authz-matrix-repository';
import type { AuthzMatrixApi } from './authz-matrix-api';

/**
 * AuthzMatrixRepositoryImpl — adapts the matrix lab API to the domain port.
 * Every thrown transport error (including the 401/403 envelopes the guarded
 * endpoints answer) is guarded into a Failed Result whose message carries
 * the engine's reason — the lab's teaching payload.
 */
export class AuthzMatrixRepositoryImpl implements AuthzMatrixRepository {
  private readonly api: AuthzMatrixApi;

  constructor(api: AuthzMatrixApi) {
    this.api = api;
  }

  panel(): Promise<Result<AuthzPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  check(
    principalName: string,
    action: string,
    scopes: string[] | null,
    resourceKind: ResourceKind | null,
    resourceId: string | null,
  ): Promise<Result<AuthzCheckOutcome>> {
    return safeRepositoryCall(() =>
      this.api.check(principalName, action, scopes, resourceKind, resourceId),
    );
  }

  editPost(credential: GuardCredential, postId: string): Promise<Result<EditedPostOutcome>> {
    return safeRepositoryCall(() => this.api.editPost(credential, postId));
  }

  moderateComment(
    credential: GuardCredential,
    commentId: string,
    status: 'visible' | 'hidden',
  ): Promise<Result<ModeratedCommentOutcome>> {
    return safeRepositoryCall(() => this.api.moderateComment(credential, commentId, status));
  }
}
