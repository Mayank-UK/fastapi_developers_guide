"""Topic 23 — Authentication (identity, secrets, and the proof of both).

Everything in this guide so far was callable by anyone; this topic is
where that ends. Six real substrates teach the whole authentication
surface: a server-side session behind an itsdangerous-sealed cookie,
API keys stored as SHA-256 hashes and compared in constant time, HS256
JWTs minted and verified with every failure mode classified, an in-repo
OAuth2 authorization server running the code grant with PKCE (S256),
argon2id password hashing with the rehash signal, and refresh-token
families whose one-time rotation turns a stolen token into an alarm.
All six demos sit INLINE in the sections that teach them, and the
terminal companion walks every endpoint with curl — cookie jar and all.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="authentication",
    title="Authentication",
    subtitle=(
        "Who are you: sessions done right with sealed cookies, API keys "
        "hashed at rest, JWTs and their trade-offs, OAuth2 with PKCE, "
        "argon2 password hashing, and refresh rotation with reuse "
        "detection — six real labs, all inline."
    ),
    group="state-auth",
    order=23,
    sections=[
        # ── 1. What authentication is ─────────────────────────────────────
        Section(
            id="what-authentication-is",
            title="What authentication is",
            blocks=[
                TextBlock(
                    kind="text",
                    id="authn-pitch",
                    text=(
                        "Authentication is the answer to WHO IS CALLING — "
                        "establishing an identity claim and checking it against "
                        "evidence. It is deliberately not the answer to WHAT MAY "
                        "THEY DO: that is authorization (topic 24), and confusing "
                        "the two is how systems end up with endpoints that check "
                        "the caller's ROLE when they meant to check the caller's "
                        "IDENTITY, or vice versa. The split is clean here: "
                        "authentication runs BEFORE the route's work and answers "
                        "with a principal (a username, a set of scopes); "
                        "authorization runs at the work itself and answers with a "
                        "verdict. Every mechanism in this topic — session cookie, "
                        "API key, JWT, OAuth-exchanged token — is only a different "
                        "way of carrying that principal across requests, and every "
                        "one of them hands topic 24 the same thing: who, and with "
                        "which scopes."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="authn-factors-pitch",
                    text=(
                        "The EVIDENCE side of authentication comes in three "
                        "kinds, called factors, and knowing them is what makes "
                        "the mechanism choices in this topic rational instead of "
                        "fashionable:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="authn-factors-list",
                    ordered=False,
                    items=[
                        "Knowledge — something the caller knows: a password, a "
                        "PIN, an API key's secret half. Cheap, revocable, and "
                        "stealable by one good phishing page or one leaked "
                        "database — never sufficient alone for anything that "
                        "matters.",
                        "Possession — something the caller has: a session cookie, "
                        "a refresh token, a phone for TOTP codes, a device key. "
                        "The workhorse factor of this topic: hard to guess, "
                        "easy to revoke server-side, and the reason logout and "
                        "rotation exist.",
                        "Inherence — something the caller is: biometrics, "
                        "hardware-bound keys. Never stored as raw data a leak "
                        "would expose (you cannot re-issue a fingerprint), which "
                        "is why real systems store derived verifier values, the "
                        "same discipline section eight teaches for passwords.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="authn-lifecycle",
                    text=(
                        "Every mechanism here walks the same lifecycle, and the "
                        "lifecycle is worth naming because each stage is a place "
                        "a design can fail. CREDENTIALS are ESTABLISHED at signup "
                        "(a password hashed, a key minted), PRESENTED at login (a "
                        "form, a header, a redirect), EXCHANGED for proof (a "
                        "session row, a token, an access grant), CARRIED on every "
                        "call (cookie, Authorization header), and — the stage "
                        "beginners forget — RETIRED: expired by TTL, revoked by "
                        "logout, rotated on suspicion. A mechanism is only as "
                        "honest as its retirement story: sessions die with a "
                        "store delete, keys die with a prefix delete, JWTs die "
                        "only with time (their weakness), and refresh families "
                        "die the moment one of their tokens is presented twice "
                        "(their whole point). Watch for that pattern as the "
                        "topic builds it six times."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="authn-substrate",
                    text=(
                        "The substrate is real and in-repo: a ``guide/domain/auth`` "
                        "package with six engines over five store ports, an "
                        "in-memory adapter seeded with two users whose argon2 "
                        "credential hashes were minted once and checked in, and a "
                        "router exposing every moving part under "
                        "``/api/demo/auth/*``. The two signing secrets it needs "
                        "(one for JWTs, one for cookie seals) live in the frozen "
                        "config with dev-only defaults — production overrides both "
                        "through environment, or the Phase 13 hardening refuses "
                        "to boot. The demo passwords are teaching facts, not "
                        "secrets: ada logs in with ``analytical-engine``, grace "
                        "with ``nanosecond``."
                    ),
                ),
            ],
        ),
        # ── 2. Login flow + cookies done right ────────────────────────────
        Section(
            id="login-flow-and-cookies",
            title="Login flow and cookies done right",
            lead="This section carries the topic's first demo — the cookie lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cookies-pitch",
                    text=(
                        "The login flow everyone recognizes is three moves: the "
                        "caller presents credentials, the server verifies them, "
                        "and the server hands back a cookie the browser will "
                        "attach to every future request. Done RIGHT, each move "
                        "carries a guarantee. The verification is "
                        "timing-uniform (an unknown username burns a decoy "
                        "hash so its rejection looks EXACTLY like a wrong "
                        "password's). The cookie value is not the session — "
                        "it is a random session id, SIGNED, with the session "
                        "itself living server-side. And the cookie's flags are "
                        "the contract: the engine states them once, as constants "
                        "the panel can quote:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cookies-constants",
                    language="py",
                    caption="The cookie contract as constants — one place, quoted everywhere.",
                    source="server/guide/domain/auth/ports.py",
                    snippet=(
                        "SESSION_COOKIE_NAME: Final = \"fdg_session\"\n"
                        "SESSION_COOKIE_PATH: Final = \"/api\"\n"
                        "SESSION_MAX_AGE_SECONDS: Final = 900\n"
                        "SESSION_COOKIE_FLAGS: Final = (\"HttpOnly\", \"SameSite=Lax\")\n"
                        "\"\"\"The flags every session cookie carries; Secure is prod-only (dev is http).\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cookies-flags",
                    text=(
                        "Each flag buys one specific protection, and the lab "
                        "sets them for real. ``HttpOnly`` tells the browser to "
                        "keep the value away from page JavaScript — an XSS "
                        "payload can run, but it cannot read the session id "
                        "out of document.cookie. ``SameSite=Lax`` stops the "
                        "browser attaching the cookie to cross-site POSTs, "
                        "which is most of the CSRF story solved at the cookie "
                        "layer (a cross-site top-level GET still carries it — "
                        "Lax is the compatibility dial, Strict the hard line). "
                        "``Secure`` forbids the cookie on plain http — correct "
                        "in production, and precisely why the DEV lab leaves "
                        "it off: the local stack is plain http, and a Secure "
                        "cookie there would simply never arrive. Path ``/api`` "
                        "scopes the cookie to the API tree so static assets "
                        "never see it either."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cookies-login-quote-pitch",
                    text=(
                        "The login itself is the whole pattern in one method: "
                        "decoy-burned verification, a 256-bit session id, the "
                        "server-side row, and the sealed cookie instruction — "
                        "note that every fact about the session (who, scopes, "
                        "expiry) lives in the STORE row, while the cookie "
                        "carries only the signed handle:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cookies-login",
                    language="py",
                    caption="Login: verify, mint the id, store the row, answer the sealed cookie.",
                    source="server/guide/domain/auth/session_service.py",
                    snippet=(
                        "        user = await self._directory.find_user(request.username)\n"
                        "        if user is None:\n"
                        "            self._passwords.verify_uniform(None, request.password)\n"
                        "            logger.info(\"session_login_rejected\", username=request.username)\n"
                        "            raise AppError(FailureKind.UNAUTHORIZED, INVALID_CREDENTIALS_MESSAGE)\n"
                        "        if not self._passwords.verify_uniform(user.password_hash, request.password):\n"
                        "            logger.info(\"session_login_rejected\", username=request.username)\n"
                        "            raise AppError(FailureKind.UNAUTHORIZED, INVALID_CREDENTIALS_MESSAGE)\n"
                        "\n"
                        "        session_id = secrets.token_urlsafe(SESSION_ID_BYTES)\n"
                        "        # …\n"
                        "        await self._store.create_session(\n"
                        "            StoredSession(\n"
                        "                session_id=session_id,\n"
                        "                username=user.username,\n"
                        "                display_name=user.display_name,\n"
                        "                scopes=user.scopes,\n"
                        "                issued_at=issued_at,\n"
                        "                expires_at=expires_at,\n"
                        "            )\n"
                        "        )\n"
                        "        sealed = self._seal_session_id(session_id)\n"
                        "        cookie = CookieInstruction(\n"
                        "            name=SESSION_COOKIE_NAME,\n"
                        "            value=sealed,\n"
                        "            max_age_seconds=SESSION_MAX_AGE_SECONDS,\n"
                        "            path=SESSION_COOKIE_PATH,\n"
                        "            httponly=True,\n"
                        "            samesite=\"lax\",\n"
                        "            secure=False,\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cookies-seal",
                    text=(
                        "The seal is itsdangerous — the same signing family "
                        "Starlette's SessionMiddleware puts behind its session "
                        "cookies. Signing is not encryption: the session id "
                        "inside is not secret, it is UNFORGEABLE — the "
                        "signature proves the value left this server, so a "
                        "client that edits one character of its cookie (say, "
                        "to probe a neighboring session id) fails the seal "
                        "check before the store is ever consulted, and every "
                        "failure mode collapses into the same answer:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cookies-open",
                    language="py",
                    caption="Open the seal: any tamper is one None — no detail, no oracle.",
                    source="server/guide/domain/auth/session_service.py",
                    snippet=(
                        "    def _open_session_id(self, cookie_value: str) -> str | None:\n"
                        "        \"\"\"Verify the signature and answer the id — None on ANY tamper.\"\"\"\n"
                        "        try:\n"
                        "            opened = self._seal.loads(cookie_value)\n"
                        "        except BadSignature:\n"
                        "            return None\n"
                        "        return opened if isinstance(opened, str) else None"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cookies-logout",
                    text=(
                        "Logout is invalidation made physical: the store row is "
                        "DELETED — not flagged — so the cookie value, or any "
                        "stolen copy of it, resolves to nothing on the very "
                        "next request; the response then expires the browser's "
                        "copy with Max-Age 0. This is the property sessions "
                        "hold over every token in this topic: revocation is a "
                        "dictionary delete, instant and total. The /me endpoint "
                        "shows the other half of the contract — missing cookie, "
                        "broken seal, unknown id, and expired row all answer "
                        "the SAME 401 envelope with no detail about which half "
                        "failed, because that detail would be an oracle."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cookies-demo-pitch",
                    text=(
                        "Try it: log in as ada and read the panel — the roster "
                        "shows the server-side row appear. Follow it with /me "
                        "and watch the sealed cookie resolve. Edit the cookie "
                        "value by one character (any HTTP client can) and /me "
                        "answers 401 without touching the store. Log out and "
                        "try /me with the OLD cookie value — dead, because the "
                        "row is gone, and that is the retirement story "
                        "section one promised."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="auth:sessions",
                    title="The cookie lab",
                    description=(
                        "The server-side session pattern, whole: POST "
                        "/sessions/login verifies the password (decoy-burned "
                        "for unknown users) and answers Set-Cookie with "
                        "HttpOnly + SameSite=Lax set for real (Secure taught "
                        "as the prod-only flag); GET /sessions/me resolves "
                        "the sealed cookie to the live session row or the "
                        "401 envelope — tampered values die at the signature; "
                        "POST /sessions/logout deletes the row so any copy of "
                        "the old cookie is instantly dead; the roster shows "
                        "every live session with its expiry."
                    ),
                ),
            ],
        ),
        # ── 3. API keys ───────────────────────────────────────────────────
        Section(
            id="api-keys",
            title="API keys",
            lead="This section carries the topic's second demo — the key lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="keys-pitch",
                    text=(
                        "A session cookie speaks for a browser; an API key "
                        "speaks for a PROGRAM — a script, a CI job, another "
                        "service. The shape the industry converged on is a "
                        "two-part key: a short readable PREFIX you can grep in "
                        "logs and recognize in a UI, and a long high-entropy "
                        "SECRET that does the proving. This guide's keys look "
                        "like ``fdg_a1b2c3d4.<43 url-safe characters>`` — eight "
                        "hex chars of prefix, 256 bits of secret — and the "
                        "split exists for the operational moments: when a key "
                        "leaks into a paste site, the prefix is how you find "
                        "every trace of it, and the secret is why finding the "
                        "prefix helps nobody."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="keys-generate-pitch",
                    text=(
                        "Generation is one honest rule enforced everywhere: "
                        "the raw key exists exactly ONCE, in the creation "
                        "response. The store receives only the SHA-256 of the "
                        "full key — plain SHA-256, not argon2, and the reason "
                        "is entropy: a password comes from a human (trillions "
                        "of possibilities at best, so verification must be "
                        "deliberately slow), while this secret is 2^256 of "
                        "machine-minted randomness, and grinding that space "
                        "is beyond anyone's budget at hash speed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="keys-generate",
                    language="py",
                    caption="Generate: readable prefix, 256-bit secret, SHA-256 at rest.",
                    source="server/guide/domain/auth/api_key_service.py",
                    snippet=(
                        "        prefix = f\"fdg_{secrets.token_hex(API_KEY_PREFIX_BYTES)}\"\n"
                        "        secret = secrets.token_urlsafe(API_KEY_SECRET_BYTES)\n"
                        "        full_key = f\"{prefix}{KEY_SEPARATOR}{secret}\"\n"
                        "        key_hash = hash_key(full_key)\n"
                        "        await self._store.save_key(\n"
                        "            StoredApiKey(\n"
                        "                prefix=prefix,\n"
                        "                name=request.name,\n"
                        "                scopes=tuple(request.scopes),\n"
                        "                key_hash=key_hash,\n"
                        "                created_at=datetime.now(UTC).isoformat(timespec=\"milliseconds\"),\n"
                        "            )\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="keys-verify-pitch",
                    text=(
                        "Verification inverts generation without ever "
                        "reconstructing the key: split the presentation at "
                        "the dot, look the record up BY PREFIX (that is why "
                        "the prefix exists on the wire — it is the database "
                        "key), hash what was presented, and compare the two "
                        "hashes. The comparison is ``hmac.compare_digest`` — "
                        "constant time, no early exit — because a plain "
                        "``==`` on hashes leaks how many leading bytes "
                        "matched through response timing, and an attacker "
                        "with a timing oracle can walk a hash byte by byte. "
                        "Even the malformed path burns a dummy comparison so "
                        "every rejection does the same shape of work:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="keys-verify",
                    language="py",
                    caption="Verify: prefix lookup, re-hash, constant-time compare.",
                    source="server/guide/domain/auth/api_key_service.py",
                    snippet=(
                        "        if KEY_SEPARATOR not in presented:\n"
                        "            hmac.compare_digest(hash_key(presented), DUMMY_KEY_HASH)\n"
                        "            raise AppError(FailureKind.UNAUTHORIZED, \"invalid api key\")\n"
                        "        prefix, _secret = presented.split(KEY_SEPARATOR, 1)\n"
                        "        record = await self._store.find_key_by_prefix(prefix)\n"
                        "        presented_hash = hash_key(presented)\n"
                        "        if record is None or not hmac.compare_digest(presented_hash, record.key_hash):\n"
                        "            logger.info(\"api_key_rejected\", prefix=prefix)\n"
                        "            raise AppError(FailureKind.UNAUTHORIZED, \"invalid api key\")\n"
                        "        logger.info(\"api_key_accepted\", prefix=prefix)\n"
                        "        return record"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="keys-scoping-revocation",
                    text=(
                        "Two production habits ride along in the record. "
                        "SCOPES make a key narrow on purpose — a read-only "
                        "deploy key carries ``posts:read`` and nothing else, "
                        "so a leaked key is a small fire (topic 24 enforces "
                        "the scopes; here they ride the record). REVOCATION "
                        "is a prefix-keyed DELETE: the record vanishes, and "
                        "the next lookup — from any copy of the key anywhere "
                        "— finds nothing. Like sessions and unlike JWTs, "
                        "keys retire instantly, which is exactly why the "
                        "next-but-one section's comparison puts them where "
                        "it does. And the discipline from generation holds "
                        "to the end: the roster shows prefixes and hash "
                        "PREVIEWS, logs carry prefixes, error envelopes "
                        "carry neither — the raw key's one appearance was "
                        "the creation response."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="keys-demo-pitch",
                    text=(
                        "Try it: generate a key and copy it — the response "
                        "warns you this is the only appearance, and the "
                        "roster below proves it (prefix + hash preview). "
                        "Call the protected endpoint with the key in the "
                        "x-api-key header: authenticated. Corrupt the secret "
                        "half and call again: 401, same envelope, same "
                        "timing shape. Revoke by prefix, then call with the "
                        "still-perfect key: 401 — the record is gone."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="auth:api-keys",
                    title="The key lab",
                    description=(
                        "The hashed-key lifecycle: POST /keys mints a "
                        "prefix + 256-bit secret pair and shows the raw key "
                        "exactly once; POST /keys/call authenticates the "
                        "x-api-key header (prefix lookup, SHA-256 re-hash, "
                        "constant-time compare) or answers the 401 envelope "
                        "— malformed, unknown prefix, and wrong secret all "
                        "indistinguishable; POST /keys/revoke deletes the "
                        "record so every copy of the key dies instantly; "
                        "the roster shows what the store really holds: "
                        "prefixes, names, scopes, hash previews."
                    ),
                ),
            ],
        ),
        # ── 4. Sessions vs keys vs tokens ─────────────────────────────────
        Section(
            id="sessions-vs-keys-vs-tokens",
            title="Sessions, keys, and tokens",
            blocks=[
                TextBlock(
                    kind="text",
                    id="compare-pitch",
                    text=(
                        "Three mechanisms now exist in this guide, and the "
                        "honest comparison is not which is BEST — each is "
                        "best somewhere — but along which AXIS they differ. "
                        "The axis that decides most architectures is WHERE "
                        "THE STATE LIVES, because that one axis determines "
                        "the revocation story, the scaling story, and the "
                        "failure story at once:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="compare-list",
                    ordered=False,
                    items=[
                        "State lives server-side (sessions) — the cookie is a "
                        "handle and the store holds the truth: revocation is a "
                        "delete (instant, total), expiry is a column, and the "
                        "cost is a lookup per request and a store that must "
                        "exist and be shared by every replica.",
                        "State lives in the credential (API keys) — the record "
                        "is the authority but the key itself is 256 bits of "
                        "self-contained proof: no expiry ceremony needed (though "
                        "records can carry one), instant revocation like "
                        "sessions, and the natural fit for non-human callers "
                        "that never had a cookie jar.",
                        "State lives in the token (JWTs) — the claims ARE the "
                        "session: verification is a signature check with zero "
                        "store reads, which scales horizontally and crosses "
                        "service boundaries beautifully, and the price is that "
                        "revocation is approximate — a signed token is true "
                        "until it expires, unless you add machinery to un-truth "
                        "it.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="compare-expiry",
                    text=(
                        "Expiry deserves its own look because it is where "
                        "the token's weakness becomes the refresh section's "
                        "reason to exist. A session's TTL is a store check "
                        "— the row is dead the moment the clock passes the "
                        "column. A key's TTL (if you set one) is the same "
                        "shape. A JWT's ``exp`` is baked INTO the token at "
                        "minting, and nothing but a new mint can change it: "
                        "a one-hour token stays valid for its hour even "
                        "after you wish it dead. That is why production "
                        "token systems keep the leash SHORT (this guide "
                        "mints 15-minute access tokens) and pair it with a "
                        "revocable long-lived credential — a session or a "
                        "refresh family — whose death stops the minting. "
                        "The pattern composes: short tokens for the calls, "
                        "revocable state for the renewals."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="compare-where",
                    text=(
                        "Where each wins, in one sentence each. Sessions win "
                        "in browsers: the cookie jar manages the credential, "
                        "logout is real, and CSRF is handled at the SameSite "
                        "layer. Keys win between programs: mint, scope, "
                        "store in a secret manager, rotate by revoking and "
                        "re-issuing. Tokens win across BOUNDARIES — service "
                        "to service, gateway to backend, anywhere the "
                        "verifier cannot or should not share a session "
                        "store — and that boundary-crossing property is "
                        "exactly why OAuth2 hands out tokens, which is the "
                        "next section's subject."
                    ),
                ),
            ],
        ),
        # ── 5. JWT ────────────────────────────────────────────────────────
        Section(
            id="jwt",
            title="JWT",
            lead="This section carries the topic's fourth demo — the token lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="jwt-anatomy",
                    text=(
                        "A JSON Web Token is three base64url parts joined by "
                        "dots: a header (the algorithm), a payload (the "
                        "claims), and a signature over the first two. The "
                        "claims are the entire point — a small, signed "
                        "dictionary the verifier can TRUST without a store "
                        "lookup: ``sub`` (who), ``iat``/``exp`` (the "
                        "validity window), ``nbf`` (not before — validity's "
                        "start gate), ``iss`` (the issuer, which the verifier "
                        "demands match its own), ``scopes`` (the authority "
                        "carried), and ``jti`` (a unique id for audit "
                        "trails). Minting is building that dictionary and "
                        "signing it — and this lab's mint has one more "
                        "honest trick: a ``sign_with: wrong`` option that "
                        "signs the SAME claims with an attacker's secret, so "
                        "the invalid-signature path is tested with a real "
                        "forgery rather than hand-edited bytes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="jwt-mint",
                    language="py",
                    caption="Mint: the claim set, and the wrong-secret forgery option.",
                    source="server/guide/domain/auth/jwt_service.py",
                    snippet=(
                        "        iat = int(moment.timestamp())\n"
                        "        expires_at_timestamp = iat + request.ttl_seconds\n"
                        "        payload: dict[str, object] = {\n"
                        "            \"sub\": request.username,\n"
                        "            \"iat\": iat,\n"
                        "            \"exp\": expires_at_timestamp,\n"
                        "            \"nbf\": iat + request.not_before_seconds,\n"
                        "            \"iss\": TOKEN_ISSUER,\n"
                        "            \"scopes\": list(request.scopes),\n"
                        "            \"jti\": str(uuid4()),\n"
                        "        }\n"
                        "        secret = self._secret if request.sign_with == \"real\" else WRONG_SECRET\n"
                        "        token = pyjwt.encode(payload, secret, algorithm=TOKEN_ALGORITHM)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="jwt-verify-pitch",
                    text=(
                        "Verification is where JWTs earn their keep and "
                        "expose their edge cases, so this engine CLASSIFIES "
                        "instead of just rejecting: PyJWT raises by "
                        "specificity, the engine catches the exception "
                        "family in order — signature FIRST, so a forged "
                        "token is labeled a forgery even when its claims "
                        "would also have expired — and every failure mode "
                        "gets a name the panel can show:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="jwt-verify",
                    language="py",
                    caption="Verify: the exception ladder — signature, expiry, nbf, shape.",
                    source="server/guide/domain/auth/jwt_service.py",
                    snippet=(
                        "        try:\n"
                        "            payload = pyjwt.decode(\n"
                        "                token,\n"
                        "                self._secret,\n"
                        "                algorithms=[TOKEN_ALGORITHM],\n"
                        "                issuer=TOKEN_ISSUER,\n"
                        "                options={\"require\": [\"sub\", \"exp\", \"iat\", \"nbf\", \"iss\"]},\n"
                        "            )\n"
                        "        except pyjwt.InvalidSignatureError:\n"
                        "            # …\n"
                        "        except pyjwt.ExpiredSignatureError:\n"
                        "            # …\n"
                        "        except pyjwt.ImmatureSignatureError:\n"
                        "            # …\n"
                        "        except pyjwt.MissingRequiredClaimError:\n"
                        "            # …\n"
                        "        except pyjwt.InvalidTokenError:\n"
                        "            # …"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="jwt-fastapi",
                    text=(
                        "FastAPI makes the carrying side idiomatic: "
                        "``OAuth2PasswordBearer`` is a dependency that reads "
                        "the Authorization header, and its ``tokenUrl`` "
                        "wires the login form into Swagger UI's "
                        "Authorize button. One deliberate divergence from "
                        "the framework default: this guide constructs it "
                        "with ``auto_error=False``, because the built-in "
                        "error raises FastAPI's bare detail shape — and the "
                        "family invariant is ONE error envelope. The guard "
                        "comes from the engine instead, classification "
                        "intact:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="jwt-scheme",
                    language="py",
                    caption="The Bearer guard, auto_error off — the envelope stays ours.",
                    source="server/guide/presentation/routers/demo/auth.py",
                    snippet=(
                        "oauth2_scheme = OAuth2PasswordBearer(\n"
                        "    tokenUrl=f\"{router.prefix}{JWT_LOGIN_PATH}\", auto_error=False\n"
                        ")\n"
                        "\"\"\"The Bearer guard FastAPI documents natively. ``auto_error=False`` keeps\n"
                        "this guide's ONE error envelope in charge of the 401 (FastAPI's built-in\n"
                        "error raises a bare detail shape) and lets the token service classify the\n"
                        "failure itself — missing, expired, forged: one envelope, named causes.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="jwt-tradeoffs",
                    text=(
                        "The trade this section's own endpoints demonstrate: "
                        "the protected route verifies with ZERO store "
                        "consults — stateless, fast, replica-proof — and "
                        "that same property means logout is theater (there "
                        "is nothing to delete) and revocation waits for "
                        "``exp``. HS256 (one shared secret signs and "
                        "verifies) suits one service or a fully trusted "
                        "cluster; RS256 splits the key pair so verifiers "
                        "hold only the public half — the right shape when "
                        "tokens must be verified by parties who must never "
                        "be able to MINT them. Neither choice changes the "
                        "revocation story; section nine does."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="jwt-demo-pitch",
                    text=(
                        "Try it: use the login form (the OAuth2 password "
                        "flow — username/password in, bearer token out), "
                        "then hit the protected endpoint with it. Mint "
                        "tokens with the dials: a 1-second TTL, then wait "
                        "and verify — expired; not-before an hour out — "
                        "not-yet-valid; sign-with wrong — bad-signature; "
                        "paste garbage — malformed. The verify panel names "
                        "every outcome, and the protected endpoint turns "
                        "every non-valid outcome into the same 401 envelope."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="auth:jwt",
                    title="The token lab",
                    description=(
                        "HS256 end to end: POST /jwt/login is the OAuth2 "
                        "password form flow (credentials in form encoding, "
                        "bearer token out); POST /jwt/mint builds tokens "
                        "with chosen scopes, TTL, not-before — and the "
                        "wrong-secret option for a real forgery; POST "
                        "/jwt/verify classifies every outcome (valid, "
                        "expired, not-yet-valid, bad-signature, malformed) "
                        "by walking PyJWT's exception ladder; GET "
                        "/jwt/protected demands the Bearer header and "
                        "answers with the caller the claims establish — or "
                        "the 401 envelope, cause named, secret never."
                    ),
                ),
            ],
        ),
        # ── 6. OAuth2 flows ───────────────────────────────────────────────
        Section(
            id="oauth2-flows",
            title="OAuth2 flows",
            lead="This section carries the topic's fifth demo — the OAuth lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="oauth-problem",
                    text=(
                        "Everything so far authenticated a caller AGAINST "
                        "YOUR server. OAuth2 solves the other problem: "
                        "letting a user grant YOUR application access to "
                        "THEIR account on someone ELSE'S server — \"sign in "
                        "with\", \"connect your calendar\" — WITHOUT the "
                        "user's password for that server ever reaching your "
                        "application. The word FLOW (grant type) names who "
                        "holds which secret, and the four worth knowing:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="oauth-grants",
                    ordered=False,
                    items=[
                        "Authorization code (with PKCE) — the browser is "
                        "redirected to the provider, consents, and comes back "
                        "with a one-time CODE the application exchanges for "
                        "tokens over a back channel; the only flow a web or "
                        "mobile app should use, and the one this section "
                        "builds for real.",
                        "Client credentials — the application IS the "
                        "principal: its own id and secret authenticate it, no "
                        "user in sight; the standard machine-to-machine grant "
                        "(and in spirit, what the API-key section already "
                        "built).",
                        "Refresh — not a login, a renewal: a long-lived, "
                        "revocable credential is exchanged for fresh access "
                        "tokens; section nine builds it with rotation and "
                        "reuse detection.",
                        "Implicit and password — the legacy pair: implicit "
                        "returned tokens in the front-channel redirect "
                        "(unsafe, obsolete), and the password grant has the "
                        "application HANDLE the user's password (only "
                        "defensible for first-party clients — which is "
                        "exactly what this guide's /jwt/login form flow is).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="oauth-pkce-pitch",
                    text=(
                        "PKCE (proof of key for code exchange) is what made "
                        "the code grant safe for clients that cannot keep a "
                        "secret — browsers, phones, CLIs. The client "
                        "generates a random VERIFIER, sends only its SHA-256 "
                        "(the CHALLENGE) with the authorize request, and "
                        "presents the verifier itself at the token exchange. "
                        "An attacker who intercepts the returning code "
                        "cannot use it: the exchange demands the verifier, "
                        "and the verifier never traveled the redirect. The "
                        "whole transform is three lines:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="oauth-s256",
                    language="py",
                    caption="S256: base64url(SHA-256(verifier)) — the one-way trip.",
                    source="server/guide/domain/auth/oauth_service.py",
                    snippet=(
                        "def s256_challenge(verifier: str) -> str:\n"
                        "    \"\"\"RFC 7636 §4.2: base64url(SHA-256(verifier)), padding stripped.\"\"\"\n"
                        "    digest = hashlib.sha256(verifier.encode(\"ascii\")).digest()\n"
                        "    return base64.urlsafe_b64encode(digest).rstrip(b\"=\").decode(\"ascii\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="oauth-exchange-pitch",
                    text=(
                        "The exchange enforces three refusals in a deliberate "
                        "ORDER. The code is consumed FIRST — one attempt, "
                        "success or failure — so a stolen code cannot be "
                        "ground against the verifier check. The redirect_uri "
                        "must EXACTLY match the authorize request's (the "
                        "registered-URI rule the authorize step already "
                        "enforced — an open redirect carrying a code is a "
                        "credential leak). And the verifier must hash to the "
                        "stored challenge, compared in constant time like "
                        "every secret in this topic:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="oauth-exchange",
                    language="py",
                    caption="The exchange: burn the code, match the redirect, prove the verifier.",
                    source="server/guide/domain/auth/oauth_service.py",
                    snippet=(
                        "        stored = await self._codes.take_code(hash_code(request.code))\n"
                        "        if stored is None:\n"
                        "            raise AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                \"invalid_grant — the code is unknown, already used, or expired \"\n"
                        "                \"(one attempt: codes are consumed on first presentation)\",\n"
                        "            )\n"
                        "        # …\n"
                        "        if request.redirect_uri != stored.redirect_uri:\n"
                        "            raise AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                \"invalid_grant — redirect_uri does not match the authorize request\",\n"
                        "            )\n"
                        "        if not hmac.compare_digest(s256_challenge(request.verifier), stored.code_challenge):\n"
                        "            logger.info(\"oauth_pkce_rejected\")\n"
                        "            raise AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                \"invalid_grant — S256(verifier) does not match the code_challenge: \"\n"
                        "                \"wrong verifier, and the code is spent\",\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="oauth-honesty",
                    text=(
                        "Honesty notes, because teaching servers should "
                        "carry them. This one SIMULATES the consent screen "
                        "(the seeded user ada approves the requested scopes; "
                        "a real server renders a page and records the "
                        "grant) and it registers exactly ONE public client "
                        "with exact-match redirect URIs — the registration "
                        "discipline that makes the redirect check "
                        "meaningful. The RFC shapes its errors as 400s with "
                        "``error=invalid_grant`` codes; this guide maps "
                        "them onto the family's 401 envelope with the "
                        "OAuth error name in the message — one envelope, "
                        "the standard's vocabulary inside it. And the "
                        "token the exchange mints is the SAME JWT section "
                        "five taught: OAuth2 does not define a token "
                        "format, it defines how you GET one — here the "
                        "answer composes with what you already know."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="oauth-demo-pitch",
                    text=(
                        "Try it: generate a PKCE pair, run authorize with "
                        "the challenge (the consent note and the redirect "
                        "URL with code+state come back), then exchange with "
                        "the verifier — the access token unlocks the "
                        "protected resource. Now the attack: authorize "
                        "again and exchange with a WRONG verifier — 401, "
                        "and the code is spent, so even the RIGHT verifier "
                        "fails after. That burned code is PKCE and "
                        "one-time-use doing their jobs in one round."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="auth:oauth",
                    title="The OAuth lab",
                    description=(
                        "A real (small) authorization server: POST "
                        "/oauth/pkce mints a verifier/challenge pair; POST "
                        "/oauth/authorize validates the registered public "
                        "client, its exact redirect_uri, and the S256 "
                        "challenge, simulates consent, and answers the "
                        "redirect with a one-time 10-minute code; POST "
                        "/oauth/token consumes the code on FIRST "
                        "presentation, matches redirect_uri exactly, and "
                        "proves the verifier in constant time — wrong "
                        "verifier is a dead code plus the 401 envelope; "
                        "GET /oauth/protected accepts the exchanged Bearer "
                        "token and checks its scope (403 without it — "
                        "topic 24's preview)."
                    ),
                ),
            ],
        ),
        # ── 7. Deciding ───────────────────────────────────────────────────
        Section(
            id="deciding",
            title="Deciding",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deciding-pitch",
                    text=(
                        "Six mechanisms, one question: WHICH, for the "
                        "caller in front of you. The decision is almost "
                        "always made by the CLIENT'S nature first and the "
                        "threat model second — everything else is "
                        "implementation. The guide's routing table, as a "
                        "list of verdicts:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="deciding-list",
                    ordered=False,
                    items=[
                        "Browser user, first-party app — a server-side "
                        "session behind a sealed cookie: logout is real, "
                        "CSRF is handled at SameSite, and the store you "
                        "already run holds the state.",
                        "Script, job, or service calling YOUR API — an API "
                        "key: prefix-greppable, scope-narrowed, instantly "
                        "revocable, and storable in every secret manager "
                        "ever shipped.",
                        "Machine-to-machine between YOUR services — short-"
                        "lived JWTs minted by a first-party login (client-"
                        "credentials-shaped): stateless verification on "
                        "every replica, no shared session store.",
                        "Third-party app acting for your USER — OAuth2 "
                        "authorization code with PKCE: the user consents, "
                        "the app never sees a password, and the token's "
                        "scopes are the consent made checkable.",
                        "Tokens that must die before they expire — pair "
                        "them with a revocable holder: a session or a "
                        "refresh family, so killing the holder stops the "
                        "minting and the damage expires naturally.",
                        "Anything that matters — two factors for humans, "
                        "narrow scopes for machines, hashed credentials at "
                        "rest, constant-time compares everywhere: the "
                        "mechanism choices above ride on those rails, "
                        "always.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="deciding-coda",
                    text=(
                        "And one non-verdict worth stating: you will "
                        "COMBINE these. The guide's own stack ends up "
                        "with cookies for the reader-facing pages, keys "
                        "for the terminal tours, JWTs behind the OAuth "
                        "exchange, and refresh families under the long "
                        "sessions — because real systems serve several "
                        "kinds of caller at once. Authentication is a "
                        "perimeter decision made per door, not per "
                        "building; topic 24 takes the principals this "
                        "topic established and finally answers what each "
                        "one is ALLOWED to do."
                    ),
                ),
            ],
        ),
        # ── 8. Password hashing ───────────────────────────────────────────
        Section(
            id="password-hashing",
            title="Password hashing (argon2)",
            lead="This section carries the topic's sixth demo — the hashing lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="hashing-pitch",
                    text=(
                        "Passwords are the credential you cannot rotate for "
                        "the user and cannot stop storing SOME form of — so "
                        "the store must hold something that verifies the "
                        "password without containing it. That is a hash, "
                        "and it is NOT encryption: encryption is two-way "
                        "(a key recovers the plaintext), while a password "
                        "hash is one-way — verification re-RUNS the "
                        "function over the candidate and compares outputs; "
                        "nothing is ever decrypted because nothing "
                        "encrypted exists. The difference is the whole "
                        "security story: a leaked password DATABASE is a "
                        "list of one-way verifiers, not a list of "
                        "passwords, and the only attack left is guessing "
                        "offline — which is exactly what the hash's COST "
                        "is priced against."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hashing-argon2",
                    text=(
                        "Argon2 (the 2015 Password Hashing Competition "
                        "winner; the ``argon2id`` variant, which this guide "
                        "uses) prices guessing in MEMORY as well as time: "
                        "each verification allocates 64 MiB and iterates, "
                        "so a laptop GPU rig that grinds SHA-1 at billions "
                        "per second grinds argon2 at tens. The engine's "
                        "defaults run about 30 milliseconds per "
                        "verification on this stack — measured honestly in "
                        "the lab, not rounded into marketing — which a "
                        "user pays once per login and an offline attacker "
                        "pays per GUESS. And a crucial subtlety the "
                        "mismatch path teaches: a WRONG password fails "
                        "AFTER the full computation, so match and mismatch "
                        "cost the same — the rejection leaks nothing."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hashing-salts",
                    text=(
                        "Every hash carries a fresh random SALT, stored "
                        "inside the hash string itself, so the same "
                        "password never hashes to the same output — which "
                        "kills rainbow tables (precomputed dictionaries "
                        "of common passwords) and hides WHICH users share "
                        "a password. The string also carries its own "
                        "PARAMETERS, and that is the quiet superpower: "
                        "``$argon2id$v=19$m=65536,t=3,p=4$…`` says 64 MiB, "
                        "3 iterations, 4 lanes, right in the credential. "
                        "When you raise the cost next year, old hashes "
                        "still verify (their parameters travel with them) "
                        "and ``needs_rehash`` flags exactly the ones to "
                        "re-hash at next successful login — the lab "
                        "carries a 2015-cost hash of ada's password to "
                        "prove the upgrade path."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hashing-login-pitch",
                    text=(
                        "The login-side rule those salts enable is the one "
                        "every login in this topic shares — unknown users "
                        "burn the SAME work as wrong passwords, against a "
                        "decoy hash, so username enumeration by response "
                        "timing finds nothing:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="hashing-uniform",
                    language="py",
                    caption="verify_uniform: unknown user, same cost, same answer.",
                    source="server/guide/domain/auth/password_service.py",
                    snippet=(
                        "    def verify_uniform(self, stored_hash: str | None, password: str) -> bool:\n"
                        "        \"\"\"The timing-uniform credential check every login uses.\n"
                        "\n"
                        "        ``stored_hash`` None (unknown username) burns a decoy verification\n"
                        "        so the answer takes the same time as a real wrong password; the\n"
                        "        result is False either way, and callers learn nothing about WHICH\n"
                        "        half failed.\n"
                        "        \"\"\"\n"
                        "        verdict = self.verify_password(\n"
                        "            VerifyPasswordRequest(password=password, hash=stored_hash or DECOY_HASH)\n"
                        "        )\n"
                        "        return verdict.ok"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hashing-bcrypt",
                    text=(
                        "bcrypt, the previous generation's standard, "
                        "remains sound where it is already deployed: "
                        "salted, adaptive (the cost factor), and "
                        "deliberately capped at 72 input bytes — the cap "
                        "is its known wart, and pre-hashing long "
                        "passphrases into it has its own famous pitfalls. "
                        "New systems choose argon2id; systems with a "
                        "bcrypt wall verify with bcrypt and rehash on "
                        "login into argon2 — the same "
                        "``needs_rehash``-on-login pattern this guide "
                        "builds. What neither forgives: storing plaintext, "
                        "encrypting instead of hashing (the key is one "
                        "leak from every password at once), logging "
                        "passwords at any layer, or timing the two "
                        "verdicts differently. The last rule is constant "
                        "across the whole topic — compare secrets in "
                        "constant time, always, from API-key digests to "
                        "PKCE challenges."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hashing-demo-pitch",
                    text=(
                        "Try it: hash any password and hash it AGAIN — two "
                        "different strings (fresh salts), both carrying "
                        "the parameters inside. Verify the right password: "
                        "ok, same milliseconds as the wrong one that "
                        "follows. Verify ada's password against the "
                        "2015-cost hash the panel ships: ok — and "
                        "needs_rehash TRUE, the upgrade flag doing its "
                        "job. The panel states the one-way distinction "
                        "where the suite can pin it."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="auth:hashing",
                    title="The hashing lab",
                    description=(
                        "argon2id with the cost shown honestly: POST "
                        "/hashing/hash mints a parameter-stamped salted "
                        "hash and reports the real elapsed milliseconds; "
                        "POST /hashing/verify runs match (right and wrong "
                        "costing the same full argon2 run) plus the "
                        "needs_rehash signal — try the panel's 2015-cost "
                        "legacy hash of ada's password to see the "
                        "upgrade path fire; the roster shows the seeded "
                        "credentials (hash previews) and the active cost "
                        "parameters."
                    ),
                ),
            ],
        ),
        # ── 9. Refresh rotation ───────────────────────────────────────────
        Section(
            id="refresh-rotation",
            title="Refresh rotation",
            lead="This section carries the topic's seventh demo — the refresh lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="refresh-problem",
                    text=(
                        "Section five's honest weakness was revocation: a "
                        "signed token is true until it expires. The naive "
                        "fix — a long-lived refresh token that buys new "
                        "access tokens — fixes the UX (no re-login every "
                        "15 minutes) and creates a new problem: a "
                        "long-lived credential is a long-lived theft "
                        "target. The modern answer makes the refresh "
                        "token's THEFT detectable: every refresh token is "
                        "ONE-TIME use, and presenting an ALREADY-USED "
                        "token is treated as proof that a copy exists "
                        "somewhere else — because two honest parties "
                        "never present the same token twice. The tokens "
                        "live in FAMILIES (one family per login), and the "
                        "detection response is to kill the entire family."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="refresh-rotation-pitch",
                    text=(
                        "Rotation is the happy path, and its bookkeeping "
                        "IS the security: the presented token is marked "
                        "used, the next link is minted into the same "
                        "family, and only the hash of each link is ever "
                        "stored — the raw successor token appears in "
                        "exactly one response:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="refresh-rotate",
                    language="py",
                    caption="Rotate: mark used, mint the next link, same family.",
                    source="server/guide/domain/auth/refresh_service.py",
                    snippet=(
                        "        moment = _utcnow()\n"
                        "        await self._store.mark_used(presented_hash, moment.isoformat(timespec=\"milliseconds\"))\n"
                        "        next_token = f\"rt_{secrets.token_urlsafe(REFRESH_TOKEN_BYTES)}\"\n"
                        "        await self._store.add_token(\n"
                        "            StoredRefreshToken(\n"
                        "                token_hash=hash_refresh_token(next_token),\n"
                        "                family_id=stored.family_id,\n"
                        "                position=stored.position + 1,\n"
                        "                status=\"active\",\n"
                        "                issued_at=moment.isoformat(timespec=\"milliseconds\"),\n"
                        "                used_at=None,\n"
                        "            ),\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="refresh-reuse-pitch",
                    text=(
                        "Reuse detection is the unhappy path done right: "
                        "the second presentation of a used token is not "
                        "an error to forgive with a fresh token — it is "
                        "an ALARM. The engine revokes the family "
                        "store-side and answers with the kill count as "
                        "proof, and every later exchange in that family "
                        "fails as invalid:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="refresh-reuse",
                    language="py",
                    caption="Reuse: the family dies as a unit — past and future links.",
                    source="server/guide/domain/auth/refresh_service.py",
                    snippet=(
                        "        if stored.status == \"used\":\n"
                        "            killed = await self._store.revoke_family(stored.family_id)\n"
                        "            self.reuse_events += 1\n"
                        "            logger.warning(\n"
                        "                \"refresh_reuse_detected\",\n"
                        "                family_id=stored.family_id,\n"
                        "                family_tokens_revoked=killed,\n"
                        "            )\n"
                        "            return RefreshExchangeRow(\n"
                        "                outcome=\"reuse-detected\",\n"
                        "                family_id=stored.family_id,\n"
                        "                # …\n"
                        "                family_tokens_revoked=killed,\n"
                        "                detail=(\n"
                        "                    f\"REUSE: position {stored.position} of family {stored.family_id} \"\n"
                        "                    f\"was already spent, so a copy exists somewhere else — the whole \"\n"
                        "                    f\"family is revoked ({killed} tokens killed, past and future). \"\n"
                        "                ),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="refresh-tradeoffs",
                    text=(
                        "The trade-off is real and worth naming: an "
                        "honest client that races itself (two tabs "
                        "refreshing at once) will occasionally trip the "
                        "alarm and be logged out — production systems "
                        "mitigate with a small grace window on just-used "
                        "tokens, accepting a sliver of risk for UX, and "
                        "the mitigation is a POLICY choice to make "
                        "deliberately, never a default to inherit. The "
                        "pattern also closes the topic's circle: short "
                        "access tokens (stateless, fast) over a revocable "
                        "family (state, instant death) — the same "
                        "composition the comparison section recommended, "
                        "now with the theft story handled. OAuth2's "
                        "refresh grant plus rotation is precisely how "
                        "production authorization servers behave today; "
                        "the lab is that behavior, small enough to watch "
                        "it happen."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="refresh-demo-pitch",
                    text=(
                        "Try it: log in — the family is born at position "
                        "1 and the raw refresh token appears once. "
                        "Exchange: the panel flips position 1 to used and "
                        "shows position 2 active. Exchange again with the "
                        "NEW token: positions march on. Now replay the "
                        "OLD position-1 token: REUSE DETECTED — the "
                        "family flips to revoked with its killed count, "
                        "and the current (position-3) token you still "
                        "hold answers 401 on its next exchange. That "
                        "collapse is the stolen-token nightmare, defused."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="auth:refresh",
                    title="The refresh lab",
                    description=(
                        "Families, rotation, and the alarm: POST "
                        "/refresh/login starts a family (first refresh "
                        "token shown raw once, stored as SHA-256); POST "
                        "/refresh/exchange is ONE-TIME use — an active "
                        "token rotates (old flips to used, next link "
                        "minted, new access token issued) while a USED "
                        "token trips reuse detection: the whole family "
                        "revoked store-side, kill count in the response, "
                        "every later exchange 401; the board shows each "
                        "family's token timeline (active/used/revoked by "
                        "position) and the engine's counters."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real cookies, real 401s, real alarms.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Eight stops: the login-logout round with a real "
                        "cookie jar, the API key's one appearance and "
                        "instant death, a JWT's whole life including its "
                        "expiry, the OAuth code+PKCE exchange, the "
                        "argon2 cost measured on your machine, and the "
                        "refresh family dying by reuse. The stack is up; "
                        "every command answers with the real envelopes "
                        "this topic built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-sessions",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the cookie round: login, authenticated call, logout, dead cookie\n"
                        "curl -s -c /tmp/fdg.jar -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"ada\",\"password\":\"analytical-engine\"}' \\\n"
                        "  localhost:8000/api/demo/auth/sessions/login \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"logged in:\", b[\"displayName\"])'\n"
                        "grep -i fdg_session /tmp/fdg.jar | head -1  # the cookie the browser would hold\n"
                        "curl -s -b /tmp/fdg.jar localhost:8000/api/demo/auth/sessions/me \\\n"
                        "  | python3 -c 'import json,sys; print(\"/me:\", json.load(sys.stdin)[\"username\"])'\n"
                        "curl -s -b /tmp/fdg.jar -X POST localhost:8000/api/demo/auth/sessions/logout > /dev/null\n"
                        "curl -s -b /tmp/fdg.jar -o /dev/null -w 'after logout: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/auth/sessions/me"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-keys",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the API key: shown once, used, revoked, instantly dead\n"
                        "KEY=$(curl -s -X POST -H 'content-type: application/json' -d '{\"name\":\"tour\"}' \\\n"
                        "  localhost:8000/api/demo/auth/keys | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"key\"])')\n"
                        "curl -s -X POST -H \"x-api-key: $KEY\" localhost:8000/api/demo/auth/keys/call \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"call ok:\", b[\"prefix\"])'\n"
                        "PREFIX=$(curl -s localhost:8000/api/demo/auth/keys \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"records\"][-1][\"prefix\"])')\n"
                        "curl -s -X POST -H 'content-type: application/json' -d \"{\\\"prefix\\\":\\\"$PREFIX\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/keys/revoke > /dev/null\n"
                        "curl -s -X POST -H \"x-api-key: $KEY\" -o /dev/null -w 'revoked: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/auth/keys/call"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-jwt",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — a JWT's whole life: form login, protected call, expiry\n"
                        "TOK=$(curl -s -X POST -d 'username=grace&password=nanosecond' \\\n"
                        "  localhost:8000/api/demo/auth/jwt/login \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"accessToken\"])')\n"
                        "curl -s -H \"Authorization: Bearer $TOK\" localhost:8000/api/demo/auth/jwt/protected \\\n"
                        "  | python3 -c 'import json,sys; print(\"protected:\", json.load(sys.stdin)[\"username\"])'\n"
                        "EXP=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"ada\",\"ttlSeconds\":1}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "sleep 2\n"
                        "curl -s -X POST -H 'content-type: application/json' -d \"{\\\"token\\\":\\\"$EXP\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/jwt/verify \\\n"
                        "  | python3 -c 'import json,sys; print(\"after ttl:\", json.load(sys.stdin)[\"outcome\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-oauth",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — OAuth code + PKCE: pair, authorize, exchange, use\n"
                        "PAIR=$(curl -s -X POST localhost:8000/api/demo/auth/oauth/pkce)\n"
                        "CH=$(echo \"$PAIR\" | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"codeChallenge\"])')\n"
                        "VF=$(echo \"$PAIR\" | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"verifier\"])')\n"
                        "CODE=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d \"{\\\"clientId\\\":\\\"guide-cli\\\",\\\"redirectUri\\\":\\\"https://client.example/callback\\\",\\\"state\\\":\\\"tour\\\",\\\"codeChallenge\\\":\\\"$CH\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/oauth/authorize \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"redirectTo\"].split(\"code=\")[1].split(\"&\")[0])')\n"
                        "AT=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d \"{\\\"code\\\":\\\"$CODE\\\",\\\"verifier\\\":\\\"$VF\\\",\\\"redirectUri\\\":\\\"https://client.example/callback\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/oauth/token \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"accessToken\"])')\n"
                        "curl -s -H \"Authorization: Bearer $AT\" localhost:8000/api/demo/auth/oauth/protected \\\n"
                        "  | python3 -c 'import json,sys; print(\"resource:\", json.load(sys.stdin)[\"username\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-hashing",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — argon2's cost, measured on this machine\n"
                        "H=$(curl -s -X POST -H 'content-type: application/json' -d '{\"password\":\"hunter2\"}' \\\n"
                        "  localhost:8000/api/demo/auth/hashing/hash \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b[\"hash\"]); import sys as s; s.stderr.write(b[\"parameters\"]+\"\\n\")')\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d \"{\\\"password\\\":\\\"hunter2\\\",\\\"hash\\\":\\\"$H\\\"}\" localhost:8000/api/demo/auth/hashing/verify \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"verify:\", b[\"ok\"], \"in\", b[\"elapsedMs\"], \"ms\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-refresh",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the refresh family: rotate, replay, watch the alarm\n"
                        "RT=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"ada\",\"password\":\"analytical-engine\"}' \\\n"
                        "  localhost:8000/api/demo/auth/refresh/login \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"refreshToken\"])')\n"
                        "RT2=$(curl -s -X POST -H 'content-type: application/json' -d \"{\\\"refreshToken\\\":\\\"$RT\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/refresh/exchange \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b[\"refreshToken\"]); s=__import__(\"sys\"); s.stderr.write(b[\"outcome\"]+\"\\n\")')\n"
                        "curl -s -X POST -H 'content-type: application/json' -d \"{\\\"refreshToken\\\":\\\"$RT\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/refresh/exchange \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"replay:\", b[\"outcome\"], \"— killed\", b[\"familyTokensRevoked\"])'\n"
                        "curl -s -X POST -H 'content-type: application/json' -d \"{\\\"refreshToken\\\":\\\"$RT2\\\"}\" \\\n"
                        "  -o /dev/null -w 'family token after alarm: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/auth/refresh/exchange"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-wrong-paths",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — the refusal paths: wrong password, tampered cookie, wrong verifier\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"ada\",\"password\":\"wrong\"}' \\\n"
                        "  -o /dev/null -w 'bad password: %{http_code}\\n' localhost:8000/api/demo/auth/sessions/login\n"
                        "curl -s -H 'Cookie: fdg_session=tampered.value' -o /dev/null -w 'tampered: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/auth/sessions/me\n"
                        "PAIR=$(curl -s -X POST localhost:8000/api/demo/auth/oauth/pkce)\n"
                        "CH=$(echo \"$PAIR\" | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"codeChallenge\"])')\n"
                        "CODE=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d \"{\\\"clientId\\\":\\\"guide-cli\\\",\\\"redirectUri\\\":\\\"https://client.example/callback\\\",\\\"codeChallenge\\\":\\\"$CH\\\"}\" \\\n"
                        "  localhost:8000/api/demo/auth/oauth/authorize \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"redirectTo\"].split(\"code=\")[1].split(\"&\")[0])')\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d \"{\\\"code\\\":\\\"$CODE\\\",\\\"verifier\\\":\\\"$(printf x%.0s {1..43})\\\",\\\"redirectUri\\\":\\\"https://client.example/callback\\\"}\" \\\n"
                        "  -o /dev/null -w 'wrong verifier: %{http_code}\\n' localhost:8000/api/demo/auth/oauth/token"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 8 — this topic: ten sections, six demos inline where they teach\n"
                        "curl -s localhost:8000/api/content/authentication | python3 -c '\n"
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
                        "Stops 1 through 3 are the carrying mechanisms — a "
                        "cookie that dies with its store row, a key that "
                        "dies with its record, a token that only dies with "
                        "time. Stop 4 is delegation done safely; stop 5 is "
                        "the cost of guessing priced honestly; stop 6 is "
                        "theft turned into an alarm; stop 7 collects the "
                        "refusals every mechanism shares. The state-and-"
                        "auth group has its identity layer; topic 24 "
                        "builds the verdict layer on top of it — who you "
                        "are is settled, what that allows is next."
                    ),
                ),
            ],
        ),
    ],
)
