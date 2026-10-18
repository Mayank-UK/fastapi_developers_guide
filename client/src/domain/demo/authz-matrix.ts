/**
 * Domain models for the authorization topic's matrix lab (demo block id
 * `authz:matrix`) — the client-side shape of the /api/demo/authz* endpoints.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is the whole model live: the seeded principals with their roles,
 * the roles→grants matrix (any = the role bypass, own = the owner check),
 * the seeded posts/comments that give ownership real objects, an interactive
 * check that runs the real policy engine, and the "try it for real" action
 * that calls a genuinely guarded endpoint with a minted credential.
 */

/** One seeded principal: name, role, and the note that teaches the punchline. */
export interface PrincipalRow {
  name: string;
  displayName: string;
  role: string | null;
  kind: 'user' | 'program';
  note: string;
}

/** One matrix cell: the action and the reach granted (null = not granted). */
export interface GrantCell {
  action: string;
  level: 'any' | 'own' | null;
}

/** One matrix row: the role and its grant cells, in action order. */
export interface RoleRow {
  role: string;
  grants: GrantCell[];
}

/** One ownership target: a seeded post and its owner. */
export interface SeededPostRow {
  id: string;
  title: string;
  author: string;
}

/** One moderation target: a seeded comment, its owner, its status. */
export interface SeededCommentRow {
  id: string;
  postId: string;
  author: string;
  status: string;
}

/** Wire shape of GET /api/demo/authz — the matrix panel's contract. */
export interface AuthzPanel {
  principals: PrincipalRow[];
  roles: RoleRow[];
  seededPosts: SeededPostRow[];
  seededComments: SeededCommentRow[];
  wildcardScope: string;
  denyNote: string;
  scopeNote: string;
  ownershipNote: string;
  checkEndpoint: string;
  editPostEndpoint: string;
  moderateCommentEndpoint: string;
  reasoning: string;
}

/** The object a verdict was computed over, when there was one. */
export interface CheckResource {
  kind: string;
  id: string;
  owner: string;
}

/** The verdict as wire: allowed, and the reason the engine gave. */
export interface CheckDecision {
  allowed: boolean;
  reason: string;
}

/** Which object kind a check targets; null means the object-less question. */
export type ResourceKind = 'post' | 'comment';

/** Wire shape of POST /api/demo/authz/check — one what-if verdict. */
export interface AuthzCheckOutcome {
  principal: string;
  role: string | null;
  scopes: string[];
  action: string;
  resource: CheckResource | null;
  decision: CheckDecision;
  detail: string;
}

/** What a guarded endpoint answers on success: who, what, and why allowed. */
export interface GuardedOutcome {
  principal: string;
  principalKind: 'user' | 'program';
  action: string;
  resourceKind: string;
  resourceId: string;
  reason: string;
  via: string;
  detail: string;
}

/** Wire shape of PUT /api/demo/authz/posts/{id} — the guarded edit (200 only). */
export interface EditedPostOutcome extends GuardedOutcome {
  post: SeededPostRow & { body: string; tags: string[]; status: string };
}

/** Wire shape of POST /api/demo/authz/comments/{id}/moderate (200 only). */
export interface ModeratedCommentOutcome extends GuardedOutcome {
  comment: SeededCommentRow & { body: string; moderatedBy: string | null };
}
