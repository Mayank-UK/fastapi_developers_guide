"""Topic 14 — webhooks (fourth topic of the APIs group).

The call reverses: the server dials the client, and every discipline
topics 11–13 built inverts with it — their URL is our dependency, their
500 is our retry budget, their slow handler is our worker pool. This
topic teaches the event catalog as a contract, the HMAC signer/verifier
pair over a shared secret (constant-time comparison included, and WHY),
the pure retry-policy engine whose exponential backoff ends at a
dead-letter queue — with the live demo ``api:webhook-simulator`` INLINE
in the retries section — receiving well (verify, park, acknowledge fast),
the honest local-development options, and the terminal curl tour last:
signed deliveries fired for real at this repo's own receive endpoint.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the domain signing and retry modules written for exactly this
teaching, the simulator builder, the demo router that carries the REAL
receive endpoint, and the endpoint test that proves tampering fails.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="webhooks",
    title="Webhooks",
    subtitle=(
        "The reversed API — your server calls out, signatures prove who "
        "rang, and retries end at a dead-letter queue."
    ),
    group="apis",
    order=14,
    sections=[
        # ── 1. Webhooks are reversed APIs ───────────────────────────────────
        Section(
            id="webhooks-are-reversed-apis",
            title="Webhooks are reversed APIs",
            blocks=[
                TextBlock(
                    kind="text",
                    id="reversed-pitch",
                    text=(
                        "Topics 11 through 13 built one shape of API: the client "
                        "asks, the server answers. But plenty of facts are not "
                        "answers to any question the client is asking — a payment "
                        "finished processing, a repository got pushed to, a video "
                        "finished transcoding. The client could poll for those "
                        "facts, and polling works, but it is the expensive "
                        "direction: a thousand clients asking every thirty "
                        "seconds burn a thousand requests to learn, most of the "
                        "time, that nothing happened. The fix is to reverse the "
                        "call. The client registers a URL once — a subscription — "
                        "and whenever the fact occurs, the SERVER sends an HTTP "
                        "request to that URL. That reversed request is a webhook."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="reversed-inversion",
                    text=(
                        "Call it reversed and mean it: every habit this guide "
                        "built inverts. On the sending side, someone else's URL "
                        "is now YOUR dependency — their 500 is your failure to "
                        "handle, their timeout is your worker sitting blocked, "
                        "their rollout that changes their response shape is your "
                        "incident. On the receiving side, YOU suddenly run an "
                        "endpoint whose callers you did not write: it must be "
                        "fast, verifiable, and idempotent, because you do not "
                        "control how often it gets called or by whom. The "
                        "vocabulary is new too, and it is worth fixing before "
                        "the rest of the topic uses it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="reversed-vocab",
                    ordered=False,
                    items=[
                        "Event — one thing that happened: a name (post.published), "
                        "an id, a payload of facts, a timestamp.",
                        "Subscription — the client's standing request to be told "
                        "about certain events, pointed at the client's URL.",
                        "Delivery — one HTTP request carrying one event to one "
                        "subscription's URL; retries make new deliveries.",
                        "Signature — an HMAC over the payload keyed by a shared "
                        "secret, proving which sender rang (section 3).",
                        "Retry policy — what the sender does when a delivery "
                        "fails: backoff, attempt budget, dead-letter queue "
                        "(section 4).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="reversed-landscape",
                    text=(
                        "This is not a niche pattern — it is how the software "
                        "economy actually moves. Payment providers tell "
                        "merchants a charge succeeded; code-forge hosts tell "
                        "build systems a push landed; SaaS platforms of every "
                        "size tell each other that a user, an invoice, or a "
                        "file changed state. The common shape: one side owns "
                        "the fact and the other side owns the reaction, "
                        "polling would couple them wastefully, and the push "
                        "decouples them — the sender does not care how long "
                        "the receiver's processing takes, only that it got a "
                        "2xx. That decoupling is also why the obligations pile "
                        "up on both sides: the sender must be patient and "
                        "verifiable, the receiver must be fast and skeptical, "
                        "and neither may assume the other is having a good day."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="reversed-repo",
                    text=(
                        "This repo now carries the whole sender-side story as "
                        "real code, in the layer the guide always puts domain "
                        "logic: guide/domain/webhooks/ owns the signer and the "
                        "retry policy, and a simulator packages them into "
                        "teachable deliveries. Because a webhook system speaks "
                        "in vocabularies before it speaks in HTTP, the code "
                        "starts exactly the way topics 11 and 13 taught API "
                        "surfaces to start — closed Literal types, so an "
                        "illegal spelling dies at the edge instead of midway "
                        "through a delivery:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="reversed-vocab-code",
                    language="py",
                    caption="The simulator's event catalog and target scenarios: closed vocabularies, like every API in this guide.",
                    source="server/guide/domain/demos/webhook_simulator.py",
                    snippet=(
                        "WebhookScenario = Literal[\"immediate-2xx\", \"always-500\", \"flaky-then-success\"]\n"
                        "\"\"\"The three target behaviors the simulator can deliver against.\"\"\"\n"
                        "\n"
                        "WebhookEventType = Literal[\"post.published\", \"post.updated\", \"comment.created\"]\n"
                        "\"\"\"The event catalog — a closed vocabulary, like every Literal in this guide.\"\"\"\n"
                        "\n"
                        "WEBHOOK_EVENT_TYPES: Final[tuple[WebhookEventType, ...]] = (\n"
                        "    \"post.published\",\n"
                        "    \"post.updated\",\n"
                        "    \"comment.created\",\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="reversed-coda",
                    text=(
                        "The rest of the topic walks the sender's obligations in "
                        "order. Section 2 designs the deliveries themselves — "
                        "what one event looks like on the wire. Section 3 adds "
                        "the signature that lets a receiver trust what arrived. "
                        "Section 4 answers the question every sender eventually "
                        "faces (the receiver was down — now what?) with backoff "
                        "and a dead-letter queue, and that section carries the "
                        "live simulator demo. Section 5 crosses the line to the "
                        "receiver's side of the contract, and section 6 deals "
                        "with the awkward truth that development happens on "
                        "localhost, where nobody can call you. The terminal "
                        "companion fires real signed deliveries at this repo's "
                        "own receive endpoint."
                    ),
                ),
            ],
        ),
        # ── 2. Designing webhook deliveries ─────────────────────────────────
        Section(
            id="designing-webhook-deliveries",
            title="Designing webhook deliveries",
            blocks=[
                TextBlock(
                    kind="text",
                    id="design-catalog",
                    text=(
                        "A webhook system's contract is its event catalog: the "
                        "names, the payload of each, and the delivery promises. "
                        "It deserves the same design care topic 11 spent on "
                        "resources, because subscribers build businesses on it — "
                        "rename an event or reshape a payload without a versioning "
                        "plan and every subscriber breaks at once. Names are "
                        "past-tense facts (post.published, not publish-post): an "
                        "event is a thing that happened, never a command to do "
                        "something. Payloads should carry the WHOLE affected "
                        "entity, not just its id, because a subscriber who gets "
                        "only an id must call back for the facts — one webhook "
                        "turns into an API round trip plus a race."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="design-envelope",
                    text=(
                        "The delivery wraps the payload in a small envelope so "
                        "the receiver can route and deduplicate before knowing "
                        "what the event is about. This repo's simulator builds "
                        "that envelope the way the guide builds every wire "
                        "shape — once, canonically, in one function — and the "
                        "canonicalization is not cosmetic. The signature in "
                        "section 3 covers the exact bytes on the wire, so the "
                        "body is serialized ONCE with sorted keys and no "
                        "incidental whitespace, and everything downstream signs "
                        "this exact string:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="design-envelope-code",
                    language="py",
                    caption="The event envelope, built as one canonical string: the bytes the signature will cover.",
                    source="server/guide/domain/demos/webhook_simulator.py",
                    snippet=(
                        "def _event_body(*, event_id: str, event_type: str, fired_at: int, note: str) -> str:\n"
                        "    \"\"\"The canonical body string: sorted keys, no incidental whitespace.\n"
                        "\n"
                        "    The signature covers THESE bytes, so the body is serialized once here\n"
                        "    and everything downstream (attempt signatures, ``deliverByHand``) uses\n"
                        "    this exact string — never a re-serialization of the parsed object.\n"
                        "    \"\"\"\n"
                        "    payload = {\n"
                        "        \"createdAt\": datetime.fromtimestamp(fired_at, tz=UTC).isoformat(),\n"
                        "        \"data\": {\"note\": note if note else \"the event's facts would live here\"},\n"
                        "        \"id\": event_id,\n"
                        "        \"type\": event_type,\n"
                        "    }\n"
                        "    return json.dumps(payload, sort_keys=True, separators=(\",\", \":\"))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="design-promises",
                    text=(
                        "Then come the promises, and subscribers read them as "
                        "harder contracts than REST clients ever did, because "
                        "they cannot retry a fact that never arrives. The "
                        "promises worth making explicitly are:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="design-promises-list",
                    ordered=False,
                    items=[
                        "At-least-once delivery — a delivery may be retried, so "
                        "it may ARRIVE twice; receivers deduplicate by event id, "
                        "never assume exactly-once.",
                        "No ordering — post.updated may arrive before "
                        "post.published if retries interleave; payloads carry "
                        "timestamps, receivers trust those, not arrival order.",
                        "Only 2xx counts — any non-2xx answer (and any timeout) "
                        "is a failure that consumes the retry budget (section 4).",
                        "Signed everything — every delivery carries the two "
                        "signature headers, so receivers never parse an "
                        "unverified body (section 3).",
                        "Versioned by name — new shapes get NEW event names or a "
                        "schemaVersion field; old shapes keep working until "
                        "retired on a published schedule.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="design-coda",
                    text=(
                        "Notice what is absent from the promises: exactly-once "
                        "ordering, guaranteed latency, or a push for every "
                        "intermediate state. Mature webhook systems (payment "
                        "providers, code hosts) publish exactly this kind of "
                        "list, and their receivers are built to survive it — "
                        "the demo's flaky scenario exists because the promise "
                        "above is honest: the SECOND delivery of an event is "
                        "not an error, it is Tuesday. The next section adds the "
                        "credential that makes any of this trustworthy."
                    ),
                ),
            ],
        ),
        # ── 3. HMAC signing ─────────────────────────────────────────────────
        Section(
            id="hmac-signing",
            title="HMAC signing",
            blocks=[
                TextBlock(
                    kind="text",
                    id="signing-threat",
                    text=(
                        "A webhook URL is a secret that must work in public: the "
                        "receiver cannot put a login in front of it, because the "
                        "sender is a machine that registered once. Anyone who "
                        "discovers the URL can POST to it — forged events, "
                        "garbage payloads, a denial-of-service aimed at the "
                        "receiver's trust. The standard answer is a shared "
                        "secret established at subscription time: sender and "
                        "receiver both know it, nobody else does, and every "
                        "delivery carries a message authentication code "
                        "computed with it. The code of choice is HMAC — a "
                        "keyed hash — built from two modules this repo already "
                        "uses everywhere: hashlib for SHA-256 and hmac for the "
                        "keyed construction. No new dependency exists in this "
                        "topic because none is needed; the standard library "
                        "settled this decades ago."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="signing-why-hmac",
                    text=(
                        "Why HMAC specifically, and not the tempting sha256(secret + "
                        "payload)? Because hashes like SHA-256 are built by "
                        "chaining an internal state block by block, and that "
                        "construction has a dark property: anyone who knows "
                        "the digest of secret + message can compute the "
                        "digest of secret + message + attacker-chosen-suffix "
                        "WITHOUT knowing the secret — the length-extension "
                        "attack. Prefixing a key to a plain hash therefore "
                        "leaves the door open to forged extensions of honestly "
                        "signed deliveries. HMAC closes it with a two-pass "
                        "construction — the message is hashed with the key "
                        "padded one way, and that result hashed again with "
                        "the key padded another — at a cost of one extra hash. "
                        "The standard library's hmac module implements it "
                        "correctly, which is exactly why this topic never "
                        "hand-rolls the arithmetic: hashlib for the primitive, "
                        "hmac for the construction, and no home-grown "
                        "cryptography anywhere."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="signing-scheme",
                    text=(
                        "The scheme this repo uses is the industry-familiar "
                        "shape. The sender computes HMAC-SHA256 over the string "
                        "timestamp.payload — the unix seconds and the EXACT "
                        "body bytes, joined by a dot — and sends two headers: "
                        "x-webhook-timestamp carrying the plain timestamp, and "
                        "x-webhook-signature carrying the hex digest prefixed "
                        "with its scheme (v1=..., so a future algorithm change "
                        "fits the same header). The timestamp is INSIDE the "
                        "signed message, not beside it: an attacker who "
                        "captures a valid delivery cannot re-date it, because "
                        "changing the timestamp changes what the signature must "
                        "cover, and cannot re-send it next week either, because "
                        "section 5's freshness window rejects it. Here is the "
                        "real signer:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="signing-sender-code",
                    language="py",
                    caption="The signer: one derivation function, one header pair — real code from the domain layer.",
                    source="server/guide/domain/webhooks/signing.py",
                    snippet=(
                        "def sign_payload(*, secret: str, timestamp: int, payload: str) -> str:\n"
                        "    \"\"\"Sign one delivery: ``v1=`` + hex HMAC-SHA256 over ``\"{timestamp}.{payload}\"``.\"\"\"\n"
                        "    return f\"{SIGNATURE_SCHEME}={_mac(secret=secret, message=f'{timestamp}.{payload}')}\"\n"
                        "\n"
                        "\n"
                        "def signed_headers(*, secret: str, timestamp: int, payload: str) -> dict[str, str]:\n"
                        "    \"\"\"The two headers a signed delivery carries — timestamp plain, MAC prefixed.\"\"\"\n"
                        "    return {\n"
                        "        TIMESTAMP_HEADER: str(timestamp),\n"
                        "        SIGNATURE_HEADER: sign_payload(secret=secret, timestamp=timestamp, payload=payload),\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="signing-verify-why",
                    text=(
                        "The receiver's half recomputes what it EXPECTS and "
                        "compares — and the comparison is where naive "
                        "implementations leak. Ordinary string equality "
                        "returns False at the first differing byte, which "
                        "means it runs for a time that depends on how many "
                        "bytes matched. An attacker who can measure response "
                        "times can forge a signature one byte position at a "
                        "time: try all 256 values of byte one, watch which "
                        "guess took microseconds longer, keep it, move on. "
                        "That is a timing attack, and the standard library's "
                        "answer is hmac.compare_digest — a comparison that "
                        "always scans everything, revealing nothing about "
                        "WHERE two signatures differ. The real verifier gates "
                        "freshness first (cheap integer arithmetic), then "
                        "compares in constant time on UTF-8 bytes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="signing-verifier-code",
                    language="py",
                    caption="The verifier: freshness gate, then hmac.compare_digest — constant time, on bytes.",
                    source="server/guide/domain/webhooks/signing.py",
                    snippet=(
                        "def verify_payload(\n"
                        "    *,\n"
                        "    secret: str,\n"
                        "    timestamp: int,\n"
                        "    signature: str,\n"
                        "    payload: str,\n"
                        "    now: int,\n"
                        "    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,\n"
                        ") -> Result[WebhookReceipt]:\n"
                        "    # … the docstring and both failure messages live in the real file\n"
                        "    age_seconds = now - timestamp\n"
                        "    if abs(age_seconds) > max_skew_seconds:\n"
                        "        return Err(\n"
                        "            AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                f\"Webhook timestamp {timestamp} is outside the ±{max_skew_seconds}s \"\n"
                        "                f\"freshness window of {now}.\",\n"
                        "            )\n"
                        "        )\n"
                        "    expected = sign_payload(secret=secret, timestamp=timestamp, payload=payload)\n"
                        "    if not hmac.compare_digest(expected.encode(\"utf-8\"), signature.encode(\"utf-8\")):\n"
                        "        return Err(\n"
                        "            AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                \"Webhook signature mismatch: the payload does not match the \"\n"
                        "                \"shared secret.\",\n"
                        "            )\n"
                        "        )\n"
                        "    return Ok(WebhookReceipt(timestamp=timestamp, age_seconds=abs(age_seconds)))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="signing-details",
                    text=(
                        "Three details in that function earn their keep in "
                        "production, not just in tests. The comparison runs on "
                        "ENCODED bytes, not the raw strings, because the "
                        "two-string form of compare_digest demands pure ASCII "
                        "and a hostile header should be rejected, never "
                        "turned into a TypeError. The function takes now as a "
                        "PARAMETER — no clock read inside — so tests pin exact "
                        "window edges without sleeping, and the caller (the "
                        "receive endpoint in section 5) decides what now "
                        "means. And the freshness window is symmetric: an "
                        "old delivery is a replay candidate and a far-future "
                        "one is a clock-skew candidate, and both are refused "
                        "before any cryptography runs. The default window is "
                        "±300 seconds — generous enough for clock drift "
                        "between datacenters, tight enough to bound replay."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="signing-secrets",
                    text=(
                        "Finally, the secret itself. Real systems generate one "
                        "per subscription, store it in a secret manager or "
                        "environment configuration (never in the repository), "
                        "and support rotation — typically by signing each "
                        "delivery with the new secret while the old one still "
                        "verifies, then retiring it. This repo does the "
                        "opposite ON PURPOSE: its demo secret is a public "
                        "constant, printed right in the simulator's payload, "
                        "because the whole lesson is that you can recompute "
                        "the HMAC yourself — the terminal companion does "
                        "exactly that. The teaching artifact is honest about "
                        "being a teaching artifact; your production code "
                        "should be honest the other way."
                    ),
                ),
            ],
        ),
        # ── 4. Retries, backoff, and the DLQ ────────────────────────────────
        Section(
            id="retries-backoff-and-the-dlq",
            title="Retries, backoff, and the DLQ",
            lead="This section carries the topic's demo — the webhook delivery simulator.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="retries-pitch",
                    text=(
                        "The receiver was down for forty seconds. Now what? "
                        "Dropping the event means the subscriber's state silently "
                        "diverges from the sender's — the worst failure mode a "
                        "webhook system has. So the sender retries, and the "
                        "at-least-once promise from section 2 is born here: "
                        "retries are WHY duplicates happen. But naive retries "
                        "are a weapon — a receiver recovering from a restart "
                        "does not need a thousand senders hammering it at "
                        "one-second intervals. The standard answer is "
                        "exponential backoff: each successive retry waits "
                        "longer, giving the recovering target room instead of "
                        "load. This repo's policy engine is PURE computation — "
                        "no sleeping, no network, just the schedule:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="retries-policy-code",
                    language="py",
                    caption="The retry policy: doubling waits, cumulative offsets — the schedule a scheduler would run.",
                    source="server/guide/domain/webhooks/retry.py",
                    snippet=(
                        "    def delay_before(self, attempt: int) -> int:\n"
                        "        \"\"\"Seconds to wait after failed ``attempt`` (1-based) before the next one.\"\"\"\n"
                        "        delay = self.base_delay_seconds\n"
                        "        for _ in range(attempt - 1):\n"
                        "            delay *= self.backoff_factor\n"
                        "        return delay\n"
                        "\n"
                        "    def scheduled_offset(self, attempt: int) -> int:\n"
                        "        \"\"\"Seconds after the fire time when ``attempt`` (1-based) runs.\n"
                        "\n"
                        "        The first attempt runs immediately (offset 0); every later one runs\n"
                        "        after the accumulated pauses of the attempts before it.\n"
                        "        \"\"\"\n"
                        "        offset = 0\n"
                        "        for prior in range(1, attempt):\n"
                        "            offset += self.delay_before(prior)\n"
                        "        return offset"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="retries-schedule",
                    text=(
                        "With the default policy — five attempts, one-second "
                        "base, doubling — the waits after failures are 1s, 2s, "
                        "4s, 8s, so the attempts themselves run at offsets 0, "
                        "1, 3, 7, and 15 seconds after the event fired. Those "
                        "numbers are exactly teachable because this engine is "
                        "deliberately JITTER-FREE; production systems add "
                        "random jitter to the same offsets so thousands of "
                        "subscriptions backing off after the same incident do "
                        "not retry in a synchronized thundering herd. Honesty "
                        "cuts both ways: the simulator shows you the clean "
                        "curve, and the curve your production metrics show "
                        "will be fuzzier for a good reason. But no budget is "
                        "infinite — five attempts is a POLICY, and when the "
                        "fifth fails, the event does not get dropped, it gets "
                        "PARKED:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="retries-dlq-code",
                    language="py",
                    caption="The budget's end: the dead-letter entry a human can inspect and replay.",
                    source="server/guide/domain/webhooks/retry.py",
                    snippet=(
                        "    final = steps[-1]\n"
                        "    return DeliveryWalk(\n"
                        "        steps=tuple(steps),\n"
                        "        verdict=\"dead-lettered\",\n"
                        "        attempts_used=policy.max_attempts,\n"
                        "        delivered_at_offset=None,\n"
                        "        dead_letter=DeadLetterEntry(\n"
                        "            event_id=event_id,\n"
                        "            attempts=policy.max_attempts,\n"
                        "            last_status=final.status,\n"
                        "            final_offset_seconds=final.offset_seconds,\n"
                        "            reason=(\n"
                        "                f\"Event {event_id} failed all {policy.max_attempts} attempts \"\n"
                        "                f\"(last answer {final.status}); parked for inspection and replay.\"\n"
                        "            ),\n"
                        "        ),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="retries-dlq-read",
                    text=(
                        "That entry is the dead-letter queue's whole reason to "
                        "exist: not a trash can but a WAITING ROOM with "
                        "paperwork. It records which event, how many attempts, "
                        "the last status the target answered, when the last "
                        "attempt ran, and a human-readable reason — everything "
                        "an on-call engineer needs at 3 a.m. to decide between "
                        "replaying the event (the receiver's outage is over) "
                        "and investigating it (the payload is poisoning one "
                        "specific handler). The demo below runs this exact "
                        "engine over three target behaviors, and each "
                        "simulated attempt is signed with section 3's real "
                        "signer at its own timestamp — a retry is a new HTTP "
                        "request, so it earns a fresh signature. Fire it:"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="api:webhook-simulator",
                    title="The webhook delivery simulator",
                    description=(
                        "GET /api/demo/api/webhook-simulator serves the roster "
                        "(scenarios, event catalog, the public teaching "
                        "secret, the exact attempt schedule); POST registers a "
                        "subscription and fires an event at the chosen target "
                        "scenario — immediate-2xx, always-500, or "
                        "flaky-then-success — and the payload walks every "
                        "delivery attempt: scheduled-at offset from the pure "
                        "backoff engine, its own signing timestamp and real "
                        "HMAC signature, the status the target answered, and "
                        "the final verdict — delivered, or the dead-letter "
                        "entry the exhausted budget minted. deliverByHand "
                        "packages a genuinely fireable signed round: fire it "
                        "at the live receive endpoint for a 202, or fire it "
                        "tampered for the 401 envelope."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="retries-demo-read",
                    text=(
                        "The simulator's router is the thin-router invariant as "
                        "usual — it mints identity and reads the clock (the "
                        "adapter's jobs, like the posts repository minting "
                        "slugs), and the PURE builder does everything else. "
                        "Note what the router hands the builder as fired_at: "
                        "one integer. Every attempt's timestamp is derived "
                        "from it deterministically, which is why the demo can "
                        "show a +15s attempt without waiting fifteen seconds "
                        "— and why the endpoint test can verify every "
                        "signature exactly:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="retries-router-code",
                    language="py",
                    caption="The simulator endpoint: the router mints ids and the clock; the pure builder walks the lifecycle.",
                    source="server/guide/presentation/routers/demo/api.py",
                    snippet=(
                        "@router.post(\n"
                        "    \"/webhook-simulator\",\n"
                        "    response_model=WebhookSimulatorPayload,\n"
                        "    response_model_exclude_none=True,\n"
                        ")\n"
                        "def run_webhook_simulator(request: WebhookSimulatorRequest) -> WebhookSimulatorPayload:\n"
                        "    \"\"\"Register a subscription + fire an event; walk the full simulated lifecycle.\"\"\"\n"
                        "    return build_webhook_simulator_payload(\n"
                        "        subscription_id=f\"sub_{uuid.uuid4().hex[:12]}\",\n"
                        "        event_id=f\"evt_{uuid.uuid4().hex[:12]}\",\n"
                        "        fired_at=int(time.time()),\n"
                        "        event_type=request.event_type,\n"
                        "        scenario=request.scenario,\n"
                        "        note=request.note,\n"
                        "        secret=DEMO_SHARED_SECRET,\n"
                        "        receive_endpoint=f\"{router.prefix}{WEBHOOK_RECEIVE_PATH}\",\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="retries-coda",
                    text=(
                        "One closing connection worth keeping: the DLQ entry "
                        "says parked for inspection and REPLAY, and replay "
                        "means sending the same event id again to a receiver "
                        "that may have already partially processed it. That is "
                        "not an edge case to apologize for — it is the "
                        "at-least-once contract working as designed, and the "
                        "receiver's duty (deduplicate by event id) is the very "
                        "first thing the next section builds into its endpoint."
                    ),
                ),
            ],
        ),
        # ── 5. Receiving well: fast 2xx ─────────────────────────────────────
        Section(
            id="receiving-well-fast-2xx",
            title="Receiving well: fast 2xx",
            blocks=[
                TextBlock(
                    kind="text",
                    id="receive-pitch",
                    text=(
                        "Cross the line: your code is now the URL somebody "
                        "else's worker dials, and their retry policy from "
                        "section 4 is aimed at YOU. A receiver that takes "
                        "eleven seconds to process a delivery gets its "
                        "connection timed out and the event re-sent — now two "
                        "copies are coming and the first is still processing. "
                        "The discipline is verify, park, acknowledge: check "
                        "the signature over the raw bytes, drop the event "
                        "somewhere durable, and return 2xx — BEFORE the "
                        "processing happens. This repo's receive endpoint is "
                        "real, live, and exactly that shape:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="receive-endpoint-code",
                    language="py",
                    caption="The real receive endpoint: raw body first, constant-time verify, then the fast 202.",
                    source="server/guide/presentation/routers/demo/api.py",
                    snippet=(
                        "async def receive_webhook(request: Request) -> WebhookReceiptPayload:\n"
                        "    \"\"\"Verify a REAL signed delivery and acknowledge fast (202 Accepted).\n"
                        "    # … the full docstring lives in the real file\n"
                        "    try:\n"
                        "        payload = (await request.body()).decode(\"utf-8\")\n"
                        "    except UnicodeDecodeError as exc:\n"
                        "        raise AppError(\n"
                        "            FailureKind.UNAUTHORIZED, \"Webhook body is not valid UTF-8.\"\n"
                        "        ) from exc\n"
                        "    # … header parsing: both headers required, timestamp must be an integer\n"
                        "    now = int(time.time())\n"
                        "    result = verify_payload(\n"
                        "        secret=DEMO_SHARED_SECRET,\n"
                        "        timestamp=timestamp,\n"
                        "        signature=signature_header,\n"
                        "        payload=payload,\n"
                        "        now=now,\n"
                        "    )\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    receipt = result.value\n"
                        "    return WebhookReceiptPayload(\n"
                        "        event_id=_signed_event_id(payload),\n"
                        "        received_at=now,\n"
                        "        age_seconds=receipt.age_seconds,\n"
                        "        detail=(\n"
                        "            \"Signature verified in constant time over the raw request bytes; \"\n"
                        "            \"accepted for processing — the 202 is already on the wire.\"\n"
                        "        ),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="receive-details",
                    text=(
                        "Read the endpoint's order of operations as a list of "
                        "deliberate refusals. It reads the RAW body before "
                        "parsing anything, because the signature covers exact "
                        "bytes and a pydantic model of the body would be a "
                        "RE-SERIALIZATION — verifying a re-serialization "
                        "verifies nothing (the endpoint test pins this: the "
                        "same JSON pretty-printed fails). It answers 202 "
                        "Accepted rather than 200, the honest status for 'in "
                        "hand, not yet processed'. It extracts only the event "
                        "id for the receipt — parsing the full payload is "
                        "processing, and processing is not what the 2xx "
                        "promised. And every failure is the family envelope: "
                        "a bad signature, a stale timestamp, a missing header, "
                        "a non-UTF-8 body — all unauthorized, all 401, all "
                        "carrying a request id like every error this guide "
                        "emits."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="receive-processing",
                    text=(
                        "What the receiver does AFTER the 2xx is the actual "
                        "work, and the pattern is always some flavor of: "
                        "append the event to durable storage keyed by event "
                        "id, return, and let background work process it. This "
                        "guide's later background-jobs topic builds that "
                        "machinery properly; the receiving-side duties do not "
                        "wait for it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="receive-duties",
                    ordered=False,
                    items=[
                        "Deduplicate by event id — the same id arriving twice "
                        "is normal at-least-once behavior, not an error to "
                        "report.",
                        "Trust payload timestamps — arrival order is not event "
                        "order once retries exist.",
                        "Never process inline — slow handlers turn into "
                        "timeouts, and timeouts turn into duplicates.",
                        "Fail loudly, not subtly — a handler that cannot "
                        "process an event should say so where humans see it, "
                        "not swallow it.",
                        "Watch the sender's posture — a spike in 5xx answers "
                        "means the sender's retry budget is being spent on "
                        "you.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="receive-coda",
                    text=(
                        "The 401-on-bad-signature answer deserves one honest "
                        "note: production receivers often collapse every "
                        "verification failure into one generic invalid "
                        "signature message, because saying WHICH gate failed "
                        "(stale versus wrong secret versus malformed) is "
                        "free reconnaissance for an attacker tuning a forgery. "
                        "This repo's verifier reports precise reasons because "
                        "it is teaching; the domain docstring says so "
                        "explicitly, and the trade is yours to make knowingly "
                        "when you ship one."
                    ),
                ),
            ],
        ),
        # ── 6. Local development ────────────────────────────────────────────
        Section(
            id="local-development",
            title="Local development",
            blocks=[
                TextBlock(
                    kind="text",
                    id="local-problem",
                    text=(
                        "Everything above assumes the sender can reach the "
                        "receiver, and development breaks that assumption "
                        "flat: your receiver runs on localhost behind no "
                        "public address, and a real provider's servers cannot "
                        "route to it. Every team that builds webhook handling "
                        "meets this on day one, and the honest options each "
                        "trade something. This repo's answer is the simulator "
                        "you already fired — sender AND receiver live in one "
                        "process, no external network, no third-party account, "
                        "and the signatures are real enough to verify by hand. "
                        "The wider ecosystem's options, conceptually:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="local-options",
                    ordered=False,
                    items=[
                        "Simulator-first (this repo) — the sender's behavior "
                        "rebuilt in-process: deterministic schedules, real "
                        "signing, zero external dependencies.",
                        "Tunnel tools — a public URL that bridges to your "
                        "localhost (ngrok, cloudflared, localtunnel-style); "
                        "convenient, but the tunnel is a moving third party "
                        "and its URL changes on restart.",
                        "Request inspectors — hosted echo endpoints that show "
                        "exactly what a provider sends (headers, body, "
                        "timing) before you write any handler.",
                        "Replay from logs — capture one real delivery, then "
                        "replay it against local code as a fixture, signature "
                        "and all.",
                        "Contract tests — encode the provider's documented "
                        "payload shapes as tests so drift fails locally, not "
                        "in production.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="local-testing",
                    text=(
                        "The cheapest local discipline is also the one this "
                        "repo practices: test the receiver through the same "
                        "signer production uses, so a green test means the "
                        "cryptography actually agreed. The endpoint test "
                        "signs a real delivery with the domain helper, fires "
                        "it through the test client, and then does the one "
                        "thing every receiver deserves a test for — proves a "
                        "tampered body cannot sneak through:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="local-test-code",
                    language="py",
                    caption="Testing a receiver locally: sign with the real helper, then tamper and expect the 401 envelope.",
                    source="server/tests/demo/test_webhook_simulator_endpoint.py",
                    snippet=(
                        "def test_tampered_body_earns_the_401_envelope(client: TestClient) -> None:\n"
                        "    body = _simulate(client, \"immediate-2xx\")\n"
                        "    hand = body[\"deliverByHand\"]\n"
                        "    tampered = hand[\"body\"].replace(\"endpoint test\", \"tampered!!!\")\n"
                        "    response = client.post(\n"
                        "        hand[\"url\"], content=tampered, headers=dict(hand[\"headers\"])\n"
                        "    )\n"
                        "    assert response.status_code == 401\n"
                        "    error = response.json()[\"error\"]\n"
                        "    assert error[\"code\"] == \"unauthorized\"\n"
                        "    assert \"signature\" in error[\"message\"]\n"
                        "    assert response.headers[\"x-request-id\"] == error[\"requestId\"]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="local-coda",
                    text=(
                        "That test is the whole local-development philosophy "
                        "in twelve lines: no mocking of the verifier, no "
                        "hand-computed digests pasted as fixtures — the real "
                        "signer produces the delivery, the real endpoint "
                        "verifies it, and the assertion watches the honest "
                        "outcome. When a provider's webhooks eventually do "
                        "reach your deployed receiver, the code that verifies "
                        "them is the same code that passed this test, which "
                        "is the strongest thing a local setup can promise."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ───────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Seven real stops: simulate, verify by hand, deliver for real, tamper, dead-letter.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour fires "
                        "the full contract by hand. Stops 1–2 read the roster "
                        "and walk the happy path; stop 3 recomputes an HMAC "
                        "with the standard library and proves the demo is not "
                        "lying about its signatures; stop 4 delivers a real "
                        "signed round at the receive endpoint (note "
                        "--data-binary — the signature covers exact bytes, so "
                        "curl must not reformat anything); stop 5 changes one "
                        "byte of that body and earns the 401 envelope; stops "
                        "6–7 watch the budget spend itself into the DLQ and "
                        "the flaky target recover on attempt three."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-roster",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the roster: scenarios, event catalog, the public secret, the schedule\n"
                        "curl -s localhost:8000/api/demo/api/webhook-simulator | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-happy",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the happy path: one attempt, one signature, delivered at +0s\n"
                        "curl -s -X POST localhost:8000/api/demo/api/webhook-simulator -H 'content-type: application/json' \\\n"
                        "  -d '{\"eventType\":\"post.published\",\"scenario\":\"immediate-2xx\",\"note\":\"terminal tour\"}' \\\n"
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-verify",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — prove the signature: recompute the HMAC over timestamp + exact bytes\n"
                        "curl -s -X POST localhost:8000/api/demo/api/webhook-simulator -H 'content-type: application/json' \\\n"
                        "  -d '{\"eventType\":\"post.updated\",\"scenario\":\"immediate-2xx\",\"note\":\"verify me\"}' | python3 -c '\n"
                        "import json, sys, hmac, hashlib\n"
                        "sim = json.load(sys.stdin)\n"
                        "d = sim[\"deliverByHand\"]\n"
                        "ts = d[\"headers\"][\"x-webhook-timestamp\"]\n"
                        "message = ts + \".\" + d[\"body\"]\n"
                        "expected = \"v1=\" + hmac.new(sim[\"secret\"].encode(), message.encode(), hashlib.sha256).hexdigest()\n"
                        "got = d[\"headers\"][\"x-webhook-signature\"]\n"
                        "print(\"sent      :\", got)\n"
                        "print(\"recomputed:\", expected)\n"
                        "print(\"MATCH\" if hmac.compare_digest(expected, got) else \"MISMATCH\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-deliver",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — deliver the SIGNED round for real: exact bytes in, 202 back\n"
                        "eval \"$(curl -s -X POST localhost:8000/api/demo/api/webhook-simulator -H 'content-type: application/json' \\\n"
                        "  -d '{\"eventType\":\"post.published\",\"scenario\":\"immediate-2xx\",\"note\":\"terminal tour\"}' | python3 -c '\n"
                        "import json, sys\n"
                        "d = json.load(sys.stdin)[\"deliverByHand\"]\n"
                        "open(\"/tmp/webhook-body.json\", \"w\").write(d[\"body\"])\n"
                        "print(\"TS=\" + repr(d[\"headers\"][\"x-webhook-timestamp\"]))\n"
                        "print(\"SIG=\" + repr(d[\"headers\"][\"x-webhook-signature\"]))')\"\n"
                        "curl -s -X POST localhost:8000/api/demo/api/webhooks/receive \\\n"
                        "  -H \"content-type: application/json\" \\\n"
                        "  -H \"x-webhook-timestamp: $TS\" -H \"x-webhook-signature: $SIG\" \\\n"
                        "  --data-binary @/tmp/webhook-body.json | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-tamper",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — tamper with one byte: same headers, different body — the 401 envelope\n"
                        "sed 's/terminal tour/tampered tour/' /tmp/webhook-body.json > /tmp/webhook-tampered.json\n"
                        "curl -s -X POST localhost:8000/api/demo/api/webhooks/receive \\\n"
                        "  -H \"content-type: application/json\" \\\n"
                        "  -H \"x-webhook-timestamp: $TS\" -H \"x-webhook-signature: $SIG\" \\\n"
                        "  --data-binary @/tmp/webhook-tampered.json | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-dlq",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the broken receiver: five 500s spend the budget; the DLQ entry is minted\n"
                        "curl -s -X POST localhost:8000/api/demo/api/webhook-simulator -H 'content-type: application/json' \\\n"
                        "  -d '{\"eventType\":\"comment.created\",\"scenario\":\"always-500\"}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "s = json.load(sys.stdin)\n"
                        "for a in s[\"attempts\"]:\n"
                        "    print(\"attempt\", a[\"attempt\"], \"at +\" + str(a[\"offsetSeconds\"]) + \"s ->\", a[\"status\"], \"(\" + a[\"outcome\"] + \")\")\n"
                        "print(\"verdict:\", s[\"verdict\"])\n"
                        "print(json.dumps(s[\"deadLetter\"], indent=2))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-flaky",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — the flaky receiver: two 500s, then 200 on the third attempt at +3s\n"
                        "curl -s -X POST localhost:8000/api/demo/api/webhook-simulator -H 'content-type: application/json' \\\n"
                        "  -d '{\"eventType\":\"post.published\",\"scenario\":\"flaky-then-success\"}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "s = json.load(sys.stdin)\n"
                        "for a in s[\"attempts\"]:\n"
                        "    print(\"attempt\", a[\"attempt\"], \"at +\" + str(a[\"offsetSeconds\"]) + \"s ->\", a[\"status\"], \"(\" + a[\"outcome\"] + \")\")\n"
                        "print(\"verdict:\", s[\"verdict\"], \"at +\" + str(s[\"deliveredAtOffset\"]) + \"s\")'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 4 is the topic's thesis in one round trip: the "
                        "bytes that left the simulator are the bytes that hit "
                        "the wire (--data-binary), the timestamp travels "
                        "beside the signature it is baked into, and the "
                        "receiver's 202 names the event id it verified — no "
                        "trust anywhere except cryptography over exact bytes. "
                        "Stop 5 is the same round with one character changed, "
                        "and the envelope answers unauthorized. You have now "
                        "run both ends of a webhook system from the terminal: "
                        "the sender that signs, schedules, retries, and "
                        "dead-letters; and the receiver that verifies in "
                        "constant time and acknowledges before processing. "
                        "The APIs group has one protocol left — topic 15 "
                        "swaps HTTP for gRPC and binary frames."
                    ),
                ),
            ],
        ),
    ],
)
