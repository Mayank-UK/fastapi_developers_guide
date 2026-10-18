import type { Result } from '../../core/result';
import type {
  AuthzCheckOutcome,
  AuthzPanel,
  EditedPostOutcome,
  ModeratedCommentOutcome,
  ResourceKind,
} from './authz-matrix';

/**
 * The credential a guarded call carries — topic 23's two shapes. The demo
 * mints Bearer tokens per principal; the API-key shape exists for the
 * program-principal round the terminal companion walks.
 */
export type GuardCredential =
  | { kind: 'bearer'; token: string }
  | { kind: 'apiKey'; key: string };

/**
 * AuthzMatrixRepository — the domain-facing port for the authorization
 * topic's matrix lab. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 *
 * The 401/403 failures of the guarded endpoints surface as Failed Results
 * (the shared error-envelope guard); the failure's message carries the
 * engine's deny reason, which is the teaching payload of this lab.
 */
export interface AuthzMatrixRepository {
  /** The panel: principals, the roles→grants matrix, targets, notes. */
  panel(): Promise<Result<AuthzPanel>>;
  /** Run the engine as a what-if: principal + action (+ object, + scopes). */
  check(
    principalName: string,
    action: string,
    scopes: string[] | null,
    resourceKind: ResourceKind | null,
    resourceId: string | null,
  ): Promise<Result<AuthzCheckOutcome>>;
  /** The guarded edit (owner-or-authority): 200 with the reason, or Failed. */
  editPost(credential: GuardCredential, postId: string): Promise<Result<EditedPostOutcome>>;
  /** The guarded moderation (admin-only): 200 with the reason, or Failed. */
  moderateComment(
    credential: GuardCredential,
    commentId: string,
    status: 'visible' | 'hidden',
  ): Promise<Result<ModeratedCommentOutcome>>;
}
