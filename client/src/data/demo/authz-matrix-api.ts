import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { GuardCredential } from '../../domain/demo/authz-matrix-repository';
import type {
  AuthzCheckOutcome,
  AuthzPanel,
  EditedPostOutcome,
  ModeratedCommentOutcome,
  ResourceKind,
} from '../../domain/demo/authz-matrix';
import {
  authzCheckFromJson,
  authzPanelFromJson,
  editedPostFromJson,
  moderatedCommentFromJson,
} from './authz-matrix-dto';

/**
 * AuthzMatrixApi — the transport for the matrix lab's endpoints. Guarded
 * calls carry the credential in its native header (Authorization: Bearer
 * for tokens, x-api-key for keys); a 403 envelope becomes a thrown
 * ServerException whose message carries the engine's deny reason.
 */

const PANEL_PATH = '/demo/authz';
const CHECK_PATH = '/demo/authz/check';
const EDIT_PATH = '/demo/authz/posts';
const MODERATE_PATH = '/demo/authz/comments';

function credentialHeaders(credential: GuardCredential): Record<string, string> {
  return credential.kind === 'bearer'
    ? { authorization: `Bearer ${credential.token}` }
    : { 'x-api-key': credential.key };
}

export class AuthzMatrixApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/authz — the matrix panel. */
  async panel(): Promise<AuthzPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, authzPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/authz/check — the engine's what-if verdict. */
  async check(
    principalName: string,
    action: string,
    scopes: string[] | null,
    resourceKind: ResourceKind | null,
    resourceId: string | null,
  ): Promise<AuthzCheckOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, CHECK_PATH, {
        method: 'POST',
        body: JSON.stringify({
          principalName,
          action,
          scopes,
          resourceKind,
          resourceId,
        }),
      });
      return parseDto(body, status, authzCheckFromJson);
    });
  }

  /** PUT {apiBaseUrl}/demo/authz/posts/{id} — the guarded edit (no-op body). */
  async editPost(credential: GuardCredential, postId: string): Promise<EditedPostOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(
        this.config,
        `${EDIT_PATH}/${postId}`,
        { method: 'PUT', headers: credentialHeaders(credential) },
      );
      return parseDto(body, status, editedPostFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/authz/comments/{id}/moderate — the admin-only guard. */
  async moderateComment(
    credential: GuardCredential,
    commentId: string,
    status: 'visible' | 'hidden',
  ): Promise<ModeratedCommentOutcome> {
    return guardedApiCall(async () => {
      const { body, status: httpStatus } = await guardedSendJson(
        this.config,
        `${MODERATE_PATH}/${commentId}/moderate`,
        {
          method: 'POST',
          headers: credentialHeaders(credential),
          body: JSON.stringify({ status }),
        },
      );
      return parseDto(body, httpStatus, moderatedCommentFromJson);
    });
  }
}
