"""Topic 24 — Authorization (the verdict layer over established identity).

Authentication answered WHO; this topic answers WHAT MAY THEY DO, and
it answers with code that runs in this repo: a pure policy engine over
a role→permission registry (deny by default, scope narrowing, ownership
rules), dependency guards that make FastAPI endpoints declare their
authority instead of checking it, and two genuinely protected resources
— a post edit guarded by ownership-or-role, a comment moderation
guarded by the admin-only action. The matrix demo sits INLINE in the
RBAC section, and the terminal companion walks every verdict with curl:
minted tokens as each principal, 403 envelopes with reasons, escalation
attempts denied.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="authorization",
    title="Authorization",
    subtitle=(
        "What may they do: RBAC roles and permissions, dependency-based "
        "enforcement, scopes that narrow, ownership that answers 'this "
        "one', and deny-by-default as the shape of every honest engine — "
        "one live matrix, two guarded endpoints."
    ),
    group="state-auth",
    order=24,
    sections=[
        # ── 1. Authentication vs authorization ────────────────────────────
        Section(
            id="authentication-vs-authorization",
            title="Authentication vs authorization",
            blocks=[
                TextBlock(
                    kind="text",
                    id="authz-two-questions",
                    text=(
                        "Authorization is the answer to WHAT MAY THE CALLER "
                        "DO — the question that only makes sense after "
                        "authentication has answered WHO IS CALLING. The "
                        "distinction survives in code because the two "
                        "failures are different accidents with different "
                        "fixes: an unauthenticated caller is a stranger "
                        "(show them the login door), while an authenticated "
                        "caller asking for too much is a member overreaching "
                        "(show them the limit). Confusing the two produces "
                        "the classic bug — an endpoint that checks the "
                        "caller's ROLE when any logged-in user should pass, "
                        "or one that only checks logged-in-ness when the "
                        "action needed a role. In this repo the split is "
                        "physical: topic 23's engines establish identity and "
                        "hand over a principal; this topic's engine takes "
                        "that principal and answers a verdict."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="authz-status-codes",
                    text=(
                        "The taxonomy encodes the split as two status codes, "
                        "and getting them right is API hygiene every client "
                        "feels: 401 UNAUTHORIZED (a naming accident — it "
                        "means UNAUTHENTICATED) says the credential is "
                        "missing or failed, and the client's correct move is "
                        "to re-authenticate; 403 FORBIDDEN says the "
                        "credential is fine and the answer is still no, and "
                        "no amount of re-logging-in will change it. The "
                        "mapping lives in one dictionary, like every "
                        "kind-to-status decision in this guide:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="authz-taxonomy-quote",
                    language="py",
                    caption="The two verdict codes, in the one mapping that owns them.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "_HTTP_STATUS_BY_KIND: dict[FailureKind, int] = {\n"
                        "    FailureKind.VALIDATION_FAILED: 422,\n"
                        "    FailureKind.UNAUTHORIZED: 401,\n"
                        "    FailureKind.FORBIDDEN: 403,\n"
                        "    # …\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="authz-principal-quote-pitch",
                    text=(
                        "The handoff point between the topics is one small "
                        "model — the PRINCIPAL. Authentication fills in "
                        "every field of it: who (``name``), how that was "
                        "established (``via``), and the authority halves "
                        "this topic's engine will read — the roles assigned "
                        "to the user and the scopes the credential carries. "
                        "Note what is deliberately ABSENT: no password "
                        "material, no token, no session id. The principal is "
                        "identity plus authority claims, nothing else, and "
                        "it is the only thing authorization ever sees:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="authz-principal-quote",
                    language="py",
                    caption="The principal: what authentication hands authorization.",
                    source="server/guide/domain/authz/model.py",
                    snippet=(
                        "class Principal(CamelModel):\n"
                        "    # …\n"
                        "    kind: PrincipalKind\n"
                        "    name: str\n"
                        "    display_name: str\n"
                        "    roles: tuple[str, ...]\n"
                        "    scopes: tuple[str, ...]\n"
                        "    via: str"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="authz-two-kinds",
                    text=(
                        "The principal comes in exactly two KINDS, and the "
                        "distinction will drive real behavior in section "
                        "four. A USER principal arrives through a Bearer "
                        "token: it has a name the directory knows, roles the "
                        "registry assigned, and the scopes riding the token's "
                        "claims. A PROGRAM principal arrives through an API "
                        "key: it has no username and NO ROLES — its scopes "
                        "are its entire authority, the client-credentials "
                        "shape. Same engine, same verdict function, two "
                        "honest ways to be somebody."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="authz-client-contract",
                    text=(
                        "Clients feel the distinction as a decision tree "
                        "they get to write once. A 401 means retry the "
                        "credential dance: refresh the token, re-present the "
                        "key, redirect to login — the request itself was "
                        "never judged. A 403 means stop: the identity is "
                        "fine, the answer is no, and the correct UI is a "
                        "message (ideally the reason string this guide's "
                        "envelope carries), not a login form the user will "
                        "complete only to meet the same 403 again. Mislabel "
                        "the two and you build exactly that maddening loop; "
                        "this is why the taxonomy maps them to different "
                        "kinds instead of one 'denied' bucket — the status "
                        "code is API UX, not ceremony."
                    ),
                ),
            ],
        ),
        # ── 2. RBAC: roles and permissions ────────────────────────────────
        Section(
            id="rbac-roles-and-permissions",
            title="RBAC: roles and permissions",
            lead="This section carries the topic's demo — the matrix lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rbac-pitch",
                    text=(
                        "Role-based access control is the workhorse model "
                        "because it gets one trade right: users are many "
                        "and CHANGING, but what people do comes in a handful "
                        "of stable shapes. Instead of granting permissions "
                        "to users directly (a matrix that grows a column "
                        "per hire), you grant permissions to ROLES and "
                        "assign roles to users — the many-to-many collapses "
                        "into two one-to-manys, and the security review "
                        "becomes 'is this table right' instead of 'audit "
                        "four thousand rows'. The vocabulary is three words: "
                        "a ROLE is a named bundle of grants, a PERMISSION "
                        "(here an ACTION like ``posts:write``) is one thing "
                        "a caller may do, and the ASSIGNMENT is who holds "
                        "which role."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rbac-registry-pitch",
                    text=(
                        "This guide's registry is pure data in the domain "
                        "layer — four roles over four actions, each grant "
                        "carrying a REACH: ``any`` (act on every object of "
                        "the kind — the role bypass) or ``own`` (act only on "
                        "objects the principal owns — the author's edge). "
                        "The whole matrix reads in one breath, and that "
                        "readability is the security property: reviewers "
                        "can hold the entire authority surface in their "
                        "heads:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rbac-table-quote",
                    language="py",
                    caption="The whole authority surface: four roles, four actions, two reaches.",
                    source="server/guide/domain/authz/roles.py",
                    snippet=(
                        "_GRANT_TABLE: Final[dict[str, tuple[GrantSpec, ...]]] = {\n"
                        "    \"viewer\": (\n"
                        "        (\"posts:read\", \"any\"),\n"
                        "        (\"comments:read\", \"any\"),\n"
                        "    ),\n"
                        "    \"author\": (\n"
                        "        (\"posts:read\", \"any\"),\n"
                        "        (\"posts:write\", \"own\"),\n"
                        "        (\"comments:read\", \"any\"),\n"
                        "    ),\n"
                        "    \"editor\": (\n"
                        "        (\"posts:read\", \"any\"),\n"
                        "        (\"posts:write\", \"any\"),\n"
                        "        (\"comments:read\", \"any\"),\n"
                        "    ),\n"
                        "    \"admin\": (\n"
                        "        (\"posts:read\", \"any\"),\n"
                        "        (\"posts:write\", \"any\"),\n"
                        "        (\"comments:read\", \"any\"),\n"
                        "        (\"comments:moderate\", \"any\"),\n"
                        "    ),\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rbac-assignments-pitch",
                    text=(
                        "Who holds which role is one more dictionary — and "
                        "the choice of names is a curriculum: the posts "
                        "substrate's authors (grace, alan, barbara) all have "
                        "real owned objects, and ada owns NOTHING, so when "
                        "the admin edits a post the reason string can only "
                        "credit the role — the bypass made visible. Failure "
                        "is also designed: a username missing from this map "
                        "resolves to no roles, and no roles means every "
                        "verdict is deny:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rbac-assignments-quote",
                    language="py",
                    caption="The assignments: four principals, four roles — absence is deny.",
                    source="server/guide/domain/authz/roles.py",
                    snippet=(
                        "ROLE_ASSIGNMENTS: Final[dict[str, str]] = {\n"
                        "    \"ada\": \"admin\",\n"
                        "    \"grace\": \"author\",\n"
                        "    \"alan\": \"viewer\",\n"
                        "    \"barbara\": \"editor\",\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rbac-why-permissions",
                    text=(
                        "One anti-pattern deserves naming before the demo, "
                        "because it is the mistake RBAC exists to prevent: "
                        "checking role STRINGS in handlers. "
                        "``if user.role == \"admin\"`` scattered across a "
                        "codebase couples every endpoint to today's org "
                        "chart — add a 'moderator' role and you hunt every "
                        "comparison; rename a role and you break authority "
                        "silently. Checking the PERMISSION instead "
                        "(``require_permission(\"comments:moderate\")``) "
                        "leaves WHO holds the grant to the registry, where "
                        "it changes in one line and the tests re-pin it in "
                        "one run. Roles are staffing; permissions are "
                        "policy; only one of them belongs in a route."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rbac-demo-pitch",
                    text=(
                        "Try it: the panel shows the four principals with "
                        "their roles and the full roles→grants matrix, plus "
                        "the seeded posts and comments the verdicts play "
                        "over. Pick any principal, action, and resource and "
                        "run the check — the REAL engine answers with a "
                        "reason (edit the scopes to watch narrowing bite: "
                        "grace with only posts:read loses her own posts). "
                        "Then run it FOR REAL: the same verdict, enforced by "
                        "a genuinely guarded endpoint against a minted "
                        "credential — 200 with the reason it allowed, or "
                        "the 403 envelope carrying the reason it did not."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="authz:matrix",
                    title="The matrix lab",
                    description=(
                        "The whole model, live: GET /api/demo/authz serves "
                        "the seeded principals, the roles→permissions matrix "
                        "(any/own reach), and the ownership targets; POST "
                        "/check runs the real policy engine as a what-if — "
                        "pick principal, action, resource, optional scopes, "
                        "and the decision comes back with its reason "
                        "(unknown principals, unknown actions, and missing "
                        "objects all deny honestly); 'try it for real' mints "
                        "a token as the chosen principal and calls the "
                        "guarded PUT /posts/{id} or moderate endpoint — the "
                        "engine verdict and the wire verdict agree, 200 or "
                        "403-with-reason."
                    ),
                ),
            ],
        ),
        # ── 3. Dependency-based enforcement ───────────────────────────────
        Section(
            id="dependency-based-enforcement",
            title="Dependency-based enforcement",
            blocks=[
                TextBlock(
                    kind="text",
                    id="enforcement-pitch",
                    text=(
                        "FastAPI has one feature that makes authorization "
                        "genuinely pleasant, and it is not an auth API — it "
                        "is the dependency system. A guard can be a "
                        "DECLARATION on the route: a dependency that runs "
                        "before the handler, resolves the principal, asks "
                        "the engine, and either lets the handler start or "
                        "raises the 403 envelope. Nothing about authority "
                        "remains in the handler body — no ``if`` on roles, "
                        "no helper someone forgot to call on the new "
                        "endpoint three months later. The guard composes "
                        "like every dependency: it is declared once in an "
                        "annotated type, every route that wants the "
                        "protection shares it, and FastAPI's per-request "
                        "cache means a request guarded twice pays for the "
                        "principal resolution once."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="enforcement-authenticate-pitch",
                    text=(
                        "The foundation dependency authenticates FIRST — "
                        "401 before any verdict, because a verdict about "
                        "nobody is meaningless. It accepts either of topic "
                        "23's credentials: the standard Bearer header (the "
                        "RFC's slot, checked first) or x-api-key for program "
                        "callers, and every failed half raises the ONE "
                        "error envelope, classified by the engine that "
                        "checked it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="enforcement-resolve-quote",
                    language="py",
                    caption="Authenticate with topic 23's engines, then resolve the principal.",
                    source="server/guide/presentation/dependencies/authz.py",
                    snippet=(
                        "    resolver = get_principal_resolver(request)\n"
                        "    if authorization is not None:\n"
                        "        scheme, _, value = authorization.partition(\" \")\n"
                        "        if scheme.lower() != \"bearer\" or not value.strip():\n"
                        "            raise AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                \"not authenticated — the Authorization header must carry \"\n"
                        "                \"'Bearer <token>'\",\n"
                        "            )\n"
                        "        username, scopes = _token_service(request).require(value.strip())\n"
                        "        return await resolver.for_token(username, scopes)\n"
                        "    if x_api_key is not None:\n"
                        "        record = await _api_key_service(request).call(x_api_key)\n"
                        "        return resolver.for_key(record)\n"
                        "    raise AppError(FailureKind.UNAUTHORIZED, NOT_AUTHENTICATED_MESSAGE)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="enforcement-factory-pitch",
                    text=(
                        "On top of that foundation sit two FACTORIES — "
                        "functions that RETURN dependencies, closing over "
                        "the action to enforce. ``require_owner_or`` is the "
                        "object-level one and the topic's thesis in one "
                        "readable shape: fetch the resource (missing means "
                        "the shared 404 the public read would answer), ask "
                        "the engine WITH the object so ownership is real, "
                        "and either hand the handler a guarded value or "
                        "never let the handler run:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="enforcement-factory-quote",
                    language="py",
                    caption="require_owner_or: the guard IS the route's authority.",
                    source="server/guide/presentation/dependencies/authz.py",
                    snippet=(
                        "    async def guard(\n"
                        "        post_id: str, request: Request, principal: PrincipalDep, engine: EngineDep\n"
                        "    ) -> GuardedPost:\n"
                        "        result = get_posts_use_cases(request).get_post.execute(post_id)\n"
                        "        if isinstance(result, Err):\n"
                        "            raise result.failure\n"
                        "        post = result.value\n"
                        "        decision = engine.decide(\n"
                        "            principal, action, OwnedResource(kind=\"post\", id=post.id, owner=post.author)\n"
                        "        )\n"
                        "        if not decision.allowed:\n"
                        "            _forbid(decision, principal, action)\n"
                        "        return GuardedPost(principal=principal, decision=decision, post=post)\n"
                        "\n"
                        "    return guard"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="enforcement-forbid-pitch",
                    text=(
                        "The deny path raises the standard envelope like "
                        "every failure in this guide — one shape, request "
                        "id, and a structured ``details`` carrying the "
                        "engine's REASON, because a 403 that says only "
                        "'forbidden' teaches the caller nothing and "
                        "generates a support ticket every time. The message "
                        "restates the reason for humans; the details carry "
                        "it for programs:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="enforcement-forbid-quote",
                    language="py",
                    caption="The 403 envelope: reason in the message, reason in the details.",
                    source="server/guide/presentation/dependencies/authz.py",
                    snippet=(
                        "    raise AppError(\n"
                        "        FailureKind.FORBIDDEN,\n"
                        "        f\"forbidden — {action} denied for {principal.name!r}: {decision.reason}\",\n"
                        "        details={\n"
                        "            \"action\": action,\n"
                        "            \"principal\": principal.name,\n"
                        "            \"principalKind\": principal.kind,\n"
                        "            \"reason\": decision.reason,\n"
                        "        },\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="enforcement-two-factories",
                    text=(
                        "The sibling factory answers the other half. "
                        "``require_permission(action)`` guards an action "
                        "with NO object — this guide's moderation endpoint "
                        "uses it — and the ordering difference is "
                        "deliberate and worth noticing on the wire: the "
                        "object guard answers 401, then 404 for a missing "
                        "post (ownership cannot be judged against nothing, "
                        "and the posts are public anyway), then 403; the "
                        "collection guard answers 401, then 403, and only "
                        "the handler's own lookup can 404. Neither order "
                        "leaks anything here, but KNOWING which you wrote "
                        "is the difference between a deliberate API and an "
                        "accidental one — and both orders put the envelope "
                        "in the client's hands with a reason inside."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="enforcement-thin-handler",
                    text=(
                        "What remains for the route is the thinnest handler "
                        "in this guide — the guard rides the signature as "
                        "an annotated dependency, and the body does only "
                        "the work the route EXISTS to do. Read it and "
                        "notice what is missing: there is no role check, "
                        "no ownership comparison, no authority concept at "
                        "all, because the dependency already answered it. "
                        "Every endpoint guarded this way gets the same "
                        "discipline for free, and adding a new protected "
                        "route is one annotation — the difference between "
                        "authorization as architecture and authorization "
                        "as choreography you hope everyone dances."
                    ),
                ),
            ],
        ),
        # ── 4. Scopes ─────────────────────────────────────────────────────
        Section(
            id="scopes",
            title="Scopes",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scopes-pitch",
                    text=(
                        "Roles say what a person's JOB allows; scopes say "
                        "what THIS CREDENTIAL allows — and the credential "
                        "is usually narrower than the person on purpose. A "
                        "deploy script runs as the author's token but only "
                        "needs ``posts:read``; a phone app gets the session "
                        "minus the admin actions. The rule that keeps this "
                        "safe is one line: scopes INTERSECT the role "
                        "grants. A scope can remove authority a role would "
                        "give; no scope can add authority the roles lack. "
                        "Get that direction wrong (union instead of "
                        "intersection) and every minted token becomes a "
                        "privilege-escalation primitive — the single "
                        "nastiest authz bug class in token-based systems."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scopes-engine-pitch",
                    text=(
                        "In the engine the narrowing is exactly the "
                        "intersection, with a deny reason that names both "
                        "halves — the role that WOULD allow and the "
                        "credential that does not:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scopes-engine-quote",
                    language="py",
                    caption="Narrowing: the intersection, with a reason that names both halves.",
                    source="server/guide/domain/authz/engine.py",
                    snippet=(
                        "        if WILDCARD_SCOPE not in principal.scopes:\n"
                        "            held = grants.get(action)\n"
                        "            if held is not None and action not in principal.scopes:\n"
                        "                return Decision(\n"
                        "                    allowed=False,\n"
                        "                    reason=(\n"
                        "                        f\"role {held.role!r} grants {action} but the credential's \"\n"
                        "                        f\"scopes {_scope_list(principal.scopes)} do not include it \"\n"
                        "                        \"— scopes narrow, never widen\"\n"
                        "                    ),\n"
                        "                )\n"
                        "            grants = {\n"
                        "                granted: grant for granted, grant in grants.items() if granted in principal.scopes\n"
                        "            }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scopes-live-example",
                    text=(
                        "The demo makes the intersection physical, using a "
                        "fact topic 23 seeded: grace's LOGIN token carries "
                        "only ``posts:read`` — so grace, an author who owns "
                        "four posts, cannot edit her own post with her own "
                        "login token. The role says yes, the credential "
                        "says no, the credential wins. Mint her a token "
                        "with the wildcard scope and the full role "
                        "authority returns. That contrast IS the lesson: "
                        "the same human, two credentials, two different "
                        "verdicts — because authorization runs on what the "
                        "CREDENTIAL carries, not on what the person is."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scopes-semantics",
                    text=(
                        "The edge semantics are decided and pinned by "
                        "tests, because undefined edges are where narrowing "
                        "bugs live. Each rule fails closed — the honest "
                        "default for anything ambiguous:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="scopes-semantics-list",
                    ordered=False,
                    items=[
                        "Wildcard scope — the ``*`` scope means full role "
                        "authority for a USER principal (the mint form's way "
                        "to skip narrowing); the engine treats it as 'do "
                        "not intersect'.",
                        "Empty scopes — a credential that carries no scopes "
                        "intersects to nothing: every action denies, with "
                        "the narrowing reason. An empty grant list is not a "
                        "wildcard.",
                        "Program credentials — an API key's scopes ARE its "
                        "grants (any-reach, no roles behind them); a "
                        "wildcard on a key denies everything, because there "
                        "are no roles for it to unlock.",
                        "Unknown scopes — a scope naming an action the "
                        "registry does not know (or a typo) grants nothing "
                        "and is silently inert; it can only narrow further.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="scopes-oauth-tie",
                    text=(
                        "Scopes are also where authorization meets OAuth2 "
                        "from topic 23 — the consent screen's checkboxes "
                        "become the token's ``scope`` claim become this "
                        "intersection. A third-party app that asked for "
                        "read-only access receives a token whose scopes "
                        "narrow whatever the user's roles would have "
                        "granted, and the resource server never needs to "
                        "know an app was involved at all: it verifies the "
                        "token, reads the scopes, intersects. That is the "
                        "whole delegation trick — consent expressed as "
                        "narrow authority, enforced by the same engine "
                        "that enforces roles, with no special case "
                        "anywhere in the verdict path."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scopes-vs-roles",
                    text=(
                        "When do scopes beat a new role? When the variation "
                        "is about the CREDENTIAL, not the person. 'Ana can "
                        "read but not write' is a role question — she is "
                        "differently employed. 'Ana's CI token can read but "
                        "not write, while Ana herself can do both' is a "
                        "scope question — same person, different "
                        "credentials, deliberately unequal. If you ever "
                        "find yourself minting roles like "
                        "author-read-only-ci to model that, you have "
                        "reimplemented scopes as role soup; give the "
                        "credential a narrowed scope list and let the "
                        "registry stay about jobs."
                    ),
                ),
            ],
        ),
        # ── 5. Ownership (object-level) ───────────────────────────────────
        Section(
            id="ownership-object-level",
            title="Ownership (object-level)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="ownership-pitch",
                    text=(
                        "RBAC answers questions about KINDS of objects — "
                        "'may this principal edit posts'. The question users "
                        "actually ask is about ONE object: 'may this "
                        "principal edit THIS post'. That is object-level "
                        "authorization, and the simplest widespread instance "
                        "is OWNERSHIP: the creator gets privileges on their "
                        "own creation that they do not get on anyone "
                        "else's. In this guide the posts substrate already "
                        "carries the fact — every post has an ``author``, "
                        "and that string is the ownership handle. The "
                        "registry's ``own`` reach turns it into policy: an "
                        "AUTHOR may write their own posts and nobody "
                        "else's, while EDITOR and ADMIN hold ``any`` reach "
                        "— the role bypass that lets moderation and "
                        "stewardship act on everyone's objects."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ownership-engine-pitch",
                    text=(
                        "The engine's object question is one small branch, "
                        "and every arm carries its reason — including the "
                        "denial that names WHO owns the object, which is "
                        "the single most useful 403 message an "
                        "object-level system can emit:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ownership-engine-quote",
                    language="py",
                    caption="The reach branch: any allows, own checks the owner — reasons on every arm.",
                    source="server/guide/domain/authz/engine.py",
                    snippet=(
                        "        if grant.level == \"any\":\n"
                        "            target = resource.kind if resource is not None else \"object\"\n"
                        "            return Decision(\n"
                        "                allowed=True,\n"
                        "                reason=(\n"
                        "                    f\"role {grant.role!r} grants {action} on any {target} — \"\n"
                        "                    \"the role is the authority\"\n"
                        "                ),\n"
                        "            )\n"
                        "        if resource is None:\n"
                        "            return Decision(\n"
                        "                allowed=False,\n"
                        "                reason=(\n"
                        "                    f\"{action} is own-scoped for role {grant.role!r} — it needs a \"\n"
                        "                    \"specific object, and none was given\"\n"
                        "                ),\n"
                        "            )\n"
                        "        if resource.owner != principal.name:\n"
                        "            return Decision(\n"
                        "                allowed=False,\n"
                        "                reason=(\n"
                        "                    f\"{action} is own-scoped, and this {resource.kind} \"\n"
                        "                    f\"{resource.id!r} belongs to {resource.owner!r}, not \"\n"
                        "                    f\"{principal.name!r}\"\n"
                        "                ),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ownership-alan-lesson",
                    text=(
                        "The demo's sharpest edge is alan: he is a VIEWER "
                        "who owns three posts, and he still cannot edit "
                        "them — ownership attaches to actions, and his "
                        "role carries no ``posts:write`` grant at any "
                        "reach. Owning the object is never sufficient by "
                        "itself; it only unlocks what a role's ``own`` "
                        "grant already half-armed. The mirror case is "
                        "grace-with-a-narrow-token from section four: the "
                        "role arms the grant, the credential narrows it "
                        "away. Authority here is ALWAYS a conjunction of "
                        "halves — role and credential, grant and object — "
                        "and every half can independently answer no."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ownership-caching-note",
                    text=(
                        "One operational note the demo makes visible: "
                        "object-level checks depend on FRESH ownership "
                        "facts. The guard here re-reads the post through "
                        "the use cases on every request, so a re-assigned "
                        "post changes verdicts immediately — but if your "
                        "resource rows ever ride a cache (topic 21), the "
                        "ownership field is part of the security decision, "
                        "and a stale owner is a stale verdict. The cheap "
                        "discipline: authorize over the same read that "
                        "feeds the write, like this guard does, and treat "
                        "any cached authority input as you would a cached "
                        "password — with a TTL you can defend."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ownership-orphans",
                    text=(
                        "Two edges deserve their own tests, because they "
                        "are where object-level checks quietly rot. The "
                        "ORPHAN object — owned by a username that has no "
                        "role assignment — behaves exactly as the rules "
                        "say: an ``any``-reach principal can still act on "
                        "it (editors are stewards of everything, including "
                        "the unowned), while an ``own``-reach principal "
                        "cannot, because the comparison is against the "
                        "caller's name, not the owner's role. And the "
                        "ANONYMOUS resource question — an own-scoped "
                        "action asked without any object — denies with "
                        "'needs a specific object', which is what keeps a "
                        "sloppy caller from interpreting a resourceless "
                        "check as a blanket yes."
                    ),
                ),
            ],
        ),
        # ── 6. Deny by default ────────────────────────────────────────────
        Section(
            id="deny-by-default",
            title="Deny by default",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deny-pitch",
                    text=(
                        "Every rule in this topic so far has been about "
                        "when to say yes. The shape that makes an "
                        "authorization system trustworthy is the opposite "
                        "one: everything the engine does not recognize is "
                        "a NO, before any grant is consulted. The engine's "
                        "first branch is the whole philosophy — the action "
                        "vocabulary is closed, and a string that is not in "
                        "it cannot be granted by anything:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deny-head-quote",
                    language="py",
                    caption="The first branch: unknown means no, before any grant is read.",
                    source="server/guide/domain/authz/engine.py",
                    snippet=(
                        "        if action not in ACTIONS:\n"
                        "            return Decision(\n"
                        "                allowed=False,\n"
                        "                reason=(\n"
                        "                    f\"unknown action {action!r} — it is not in the registry, \"\n"
                        "                    \"and the engine denies what it does not know\"\n"
                        "                ),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deny-principal-quote-pitch",
                    text=(
                        "The same fail-closed logic guards the principal "
                        "side: a caller whose username has no assignment "
                        "resolves to zero roles, zero roles contribute "
                        "zero grants, and the deny comes with a reason "
                        "that says exactly that. Unknown ROLES inside an "
                        "assignment list are inert the same way — a "
                        "renamed role does not silently keep its old "
                        "powers, it just stops contributing:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deny-principal-quote",
                    language="py",
                    caption="No roles, no grants — the assignment's absence is the answer.",
                    source="server/guide/domain/authz/engine.py",
                    snippet=(
                        "        grants = self._role_grants(principal)\n"
                        "        if not grants:\n"
                        "            return Decision(\n"
                        "                allowed=False,\n"
                        "                reason=(\n"
                        "                    f\"{principal.name!r} has no role in the registry — \"\n"
                        "                    \"deny by default\"\n"
                        "                ),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deny-fail-open",
                    text=(
                        "Fail-OPEN is what this shape prevents, and it is "
                        "worth seeing the bug in the wild so the pattern "
                        "registers. The classics: a check that catches an "
                        "exception from the role lookup and returns True "
                        "('better available than locked out'); a default "
                        "role of 'user' assigned to every unresolvable "
                        "name; a front-end that hides the button and a "
                        "backend that never checks; a new action added to "
                        "the product before it is added to the registry, "
                        "gated by a wildcard grant someone added 'temporarily'. "
                        "Each one is generous in a place that must be "
                        "strict. The test is always the same sentence: "
                        "delete the registry entry, misspell the action, "
                        "present a token from a dead issuer — and the "
                        "answer must be 403 (or 401), never 200."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deny-observability",
                    text=(
                        "Denials are also the best security log you will "
                        "ever have, and the fail-closed shape makes them "
                        "honest. Every 403 this guide emits rides the "
                        "shared envelope with the request id and the "
                        "engine's reason, so the log line answers the "
                        "question incident responders actually ask — WHO "
                        "tried WHAT on WHICH object and WHY was it "
                        "refused — without any extra instrumentation. A "
                        "cluster of narrowing denials from one principal "
                        "is a mis-scoped token; a sprinkling of "
                        "unknown-action denials is a client speaking last "
                        "month's vocabulary; one escalation-shaped denial "
                        "(a viewer hammering admin actions) is worth a "
                        "look. Fail-open systems cannot offer this signal "
                        "because their mistakes succeed quietly."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deny-testing",
                    text=(
                        "This is why the engine's test suite pins the "
                        "NEGATIVE space as deliberately as the matrix "
                        "itself: unknown action denies, unknown principal "
                        "denies, unknown role contributes nothing, empty "
                        "scopes deny, missing objects deny, own-scoped "
                        "without an object denies. Allow paths are easy to "
                        "remember to test; the deny paths are the ones "
                        "that only show up in an incident report. A pure "
                        "engine makes them one-line assertions instead — "
                        "another dividend of keeping the policy out of "
                        "the handlers."
                    ),
                ),
            ],
        ),
        # ── 7. In the wild ────────────────────────────────────────────────
        Section(
            id="in-the-wild",
            title="In the wild",
            blocks=[
                TextBlock(
                    kind="text",
                    id="wild-pitch",
                    text=(
                        "RBAC-plus-ownership covers a remarkable share of "
                        "real systems, but the industry has grown other "
                        "shapes for the cases it does not fit, and knowing "
                        "their names — and their PRICE — is how you avoid "
                        "reaching for them early. The survey, honestly "
                        "priced:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="wild-models",
                    ordered=False,
                    items=[
                        "ACLs (access control lists) — a per-object list of "
                        "who may act: the operating-system heritage (files, "
                        "buckets). Precise per object, but reviewing 'who "
                        "can do X everywhere' means walking every list, and "
                        "the lists multiply with the objects.",
                        "ABAC (attribute-based) — rules over ATTRIBUTES of "
                        "principal, resource, and context ('editors in "
                        "region EU during business hours on posts tagged "
                        "public'): expressive, and the policies become "
                        "programs that need their own testing and debugging "
                        "discipline.",
                        "ReBAC (relationship-based) — Google's Zanzibar "
                        "lineage: authorization as a graph query over "
                        "relations ('viewer of folder that contains "
                        "document'). The natural fit for shared-drive "
                        "shapes — and a graph database plus a policy "
                        "language you now operate.",
                        "Policy engines (OPA, Cedar, Casbin) — the decision "
                        "pulled out of the app into a dedicated evaluator "
                        "with its own policy syntax: one brain for many "
                        "services, at the cost of a second system to "
                        "version, test, and deploy.",
                        "Scope-narrowed tokens (OAuth/OIDC) — grants lived "
                        "IN the credential (this guide's section four): "
                        "perfect for delegation across trust boundaries, "
                        "with revocation's known weakness priced in topic "
                        "23.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="wild-this-guide",
                    text=(
                        "Where this guide's own choice sits in that "
                        "landscape, said plainly: the registry-plus-engine "
                        "in ``guide/domain/authz`` is RBAC with an "
                        "ownership relation and a scope intersection — no "
                        "policy language, no engine service, roughly a "
                        "hundred lines of pure Python you have now read "
                        "all of. That is not a toy concession; it is the "
                        "same seam Zanzibar or OPA would sit behind. When "
                        "a heavier model earns its operating cost, the "
                        "guards, the reason strings, the tests' matrix "
                        "pins, and the endpoints all survive — only the "
                        "function behind ``decide`` grows teeth."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="wild-choosing",
                    text=(
                        "The decision sequence that ages well: start with "
                        "RBAC over a closed action vocabulary, add "
                        "ownership when objects have creators, narrow with "
                        "scopes when credentials must be smaller than "
                        "people — and only when a requirement genuinely "
                        "cannot be said in that vocabulary (arbitrary "
                        "sharing graphs, context-dependent rules across "
                        "many services) reach for the heavier models, "
                        "ideally behind a policy engine so the app keeps "
                        "one seam. Every one of those steps is reversible "
                        "if the decision stays behind an interface shaped "
                        "like this guide's engine — a pure function from "
                        "(principal, action, resource) to a verdict with a "
                        "reason. That seam, not any particular model, is "
                        "the architectural decision."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real verdicts, real 403 reasons.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Seven stops: the panel and a simulated verdict, "
                        "the author editing her own post, the escalation "
                        "attempts that fail with reasons worth reading, "
                        "the role bypass, the admin-only moderation, the "
                        "narrowed credential losing what the role would "
                        "give, and the program principal (an API key) "
                        "carrying exactly its scopes. The stack is up; "
                        "every command answers with the real envelopes "
                        "this topic built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the matrix, then a simulated verdict from the real engine\n"
                        "curl -s localhost:8000/api/demo/authz \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"principals:\", [(p[\"name\"], p[\"role\"]) for p in b[\"principals\"]])'\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"principalName\":\"barbara\",\"action\":\"posts:write\",\"resourceKind\":\"post\",\"resourceId\":\"designing-urls-people-can-read\"}' \\\n"
                        "  localhost:8000/api/demo/authz/check \\\n"
                        "  | python3 -c 'import json,sys; d=json.load(sys.stdin)[\"decision\"]; print(d[\"allowed\"], \"—\", d[\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-own-post",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the author edits HER post: mint grace a full-authority token\n"
                        "GRACE=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"grace\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -X PUT -H \"Authorization: Bearer $GRACE\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b[\"principal\"], \"—\", b[\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-escalation",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — escalation attempts: grace on alan's post, alan (the OWNER!) as viewer\n"
                        "curl -s -X PUT -o /dev/null -w 'grace on alan post: %{http_code}\\n' \\\n"
                        "  -H \"Authorization: Bearer $GRACE\" localhost:8000/api/demo/authz/posts/idempotency-retold\n"
                        "curl -s -X PUT -H \"Authorization: Bearer $GRACE\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/idempotency-retold \\\n"
                        "  | python3 -c 'import json,sys; print(\"  reason:\", json.load(sys.stdin)[\"error\"][\"details\"][\"reason\"])'\n"
                        "ALAN=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"alan\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -X PUT -H \"Authorization: Bearer $ALAN\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/idempotency-retold \\\n"
                        "  | python3 -c 'import json,sys; print(\"alan owns it but:\", json.load(sys.stdin)[\"error\"][\"details\"][\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-bypass-moderation",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the role bypass (editor) and the admin-only moderation\n"
                        "BARBARA=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"barbara\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -X PUT -H \"Authorization: Bearer $BARBARA\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"editor on grace post:\", b[\"reason\"])'\n"
                        "curl -s -X POST -H \"Authorization: Bearer $BARBARA\" -H 'content-type: application/json' \\\n"
                        "  -d '{\"status\":\"hidden\"}' -o /dev/null -w 'editor moderates: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/authz/comments/urls-are-for-machines/moderate\n"
                        "ADA=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"ada\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -X POST -H \"Authorization: Bearer $ADA\" -H 'content-type: application/json' \\\n"
                        "  -d '{\"status\":\"visible\"}' localhost:8000/api/demo/authz/comments/urls-are-for-machines/moderate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"admin moderates:\", b[\"comment\"][\"status\"], \"—\", b[\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-narrowing",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — scope narrowing: grace's own post, but a token that forgot the write\n"
                        "NARROW=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"grace\",\"scopes\":[\"posts:read\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -X PUT -H \"Authorization: Bearer $NARROW\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read \\\n"
                        "  | python3 -c 'import json,sys; print(\"narrowed:\", json.load(sys.stdin)[\"error\"][\"details\"][\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-key",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the program principal: an API key carrying exactly its scopes\n"
                        "KEY=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"name\":\"authz tour\",\"scopes\":[\"posts:write\"]}' localhost:8000/api/demo/auth/keys \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"key\"])')\n"
                        "curl -s -X PUT -H \"x-api-key: $KEY\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"key:\", b[\"principal\"], \"—\", b[\"reason\"])'\n"
                        "READKEY=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"name\":\"read only\",\"scopes\":[\"posts:read\"]}' localhost:8000/api/demo/auth/keys \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"key\"])')\n"
                        "curl -s -X PUT -H \"x-api-key: $READKEY\" \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read \\\n"
                        "  | python3 -c 'import json,sys; print(\"read key:\", json.load(sys.stdin)[\"error\"][\"details\"][\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-refusals",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — the refusal ladder: 401 before you are anyone, 403 once you are\n"
                        "curl -s -X PUT -o /dev/null -w 'no credential: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read\n"
                        "curl -s -X PUT -o /dev/null -w 'forged token:  %{http_code}\\n' \\\n"
                        "  -H 'Authorization: Bearer not.a.token' \\\n"
                        "  localhost:8000/api/demo/authz/posts/designing-urls-people-can-read\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"principalName\":\"ghost\",\"action\":\"posts:write\"}' \\\n"
                        "  localhost:8000/api/demo/authz/check \\\n"
                        "  | python3 -c 'import json,sys; d=json.load(sys.stdin)[\"decision\"]; print(\"ghost:\", d[\"allowed\"], \"—\", d[\"reason\"])'\n"
                        "curl -s localhost:8000/api/content/authorization | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 2 through 4 walk the matrix's rows with real "
                        "credentials — ownership allowing, ownership "
                        "denying, the bypass overriding both. Stop 5 shows "
                        "the credential winning an argument with the role; "
                        "stop 6 shows a principal with no roles at all "
                        "carrying exactly its scopes; stop 7 collects the "
                        "ladder every request climbs — 401, then 403, then "
                        "200. The state-and-auth group is now complete at "
                        "the core: topic 25 broadens from authority to "
                        "threats — headers, rate limits, injection, and "
                        "the habits that keep all of this honest in "
                        "production."
                    ),
                ),
            ],
        ),
    ],
)
