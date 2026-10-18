"""Topic 10 — validation (fourth and final topic of the Request handling group).

Why validation belongs at the boundary, taught against this server's real
code: the three layers that guard an edge · pydantic at the edge and the
422 envelope (with the topic's live demo ``validation:arena`` INLINE in
that section) · Field constraints + Annotated · custom validators ·
model-level and composed validation · choosing an approach — and the
terminal curl tour last.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the error taxonomy's RequestValidationError handler and its recorded
422-vs-400 family decision, the scenario store's domain-layer revalidation,
the roster models the arena judges (the notes playground's body, the pyd
lab's specimen, the scenario PATCH), the lab's field and model validators,
the content registry's hand-rolled composed validation — and this topic's
own arena (builder + router, written for exactly this teaching).
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="validation",
    title="Validation",
    subtitle=(
        "Why untrusted input dies at the boundary — the three layers that "
        "guard it, pydantic's 422 vocabulary, and how much checking belongs "
        "at the edge versus inside the domain."
    ),
    group="request-handling",
    order=10,
    sections=[
        # ── 1. Why validate at the boundary ────────────────────────────────
        Section(
            id="why-validate-at-the-boundary",
            title="Why validate at the boundary",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-boundary-pitch",
                    text=(
                        "Everything topic 09 let into a handler was already "
                        "typed, but the wire is not. A request body is bytes "
                        "a stranger chose: the JSON may be malformed, the "
                        "title may be eighty thousand characters, the score "
                        "may be a string, the id may be negative, and the "
                        "``tags`` may be a dictionary where a list belongs. "
                        "The question this topic answers is WHERE that "
                        "hostility gets answered — and the answer this whole "
                        "family of guides gives is: as far out as possible. "
                        "Validation at the boundary means the check runs "
                        "before your code does, so every line after it — "
                        "handler, use case, store — operates on values that "
                        "are already the right type, already within bounds, "
                        "already canonical. Nothing downstream carries the "
                        "burden of doubting its own inputs."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-boundary-cost",
                    text=(
                        "The alternative is checking late, and it fails in "
                        "two directions at once. Check too little and a "
                        "garbage value travels: it gets stored, logged, "
                        "serialized back to other clients, or detonates "
                        "three layers in with a traceback the client cannot "
                        "act on. Check too much, scattered — the same "
                        "``if not title`` in the router, the use case, and "
                        "the store — and the rules drift apart, so the "
                        "store accepts what the router refuses and the "
                        "tests disagree with production. A typed model at "
                        "the edge fixes both: the rule is written once, "
                        "where the contract is declared, and everything "
                        "inside the boundary inherits it for free. Topic 05 "
                        "taught the pydantic pipeline itself; topic 09 put "
                        "it to work on real bodies. This topic is the "
                        "discipline around that machinery — the layers, the "
                        "vocabulary of constraints and validators, and the "
                        "shape of the refusal a bad body earns."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-boundary-arena-tease",
                    text=(
                        "One more pitch before the theory: validation is "
                        "best believed when watched, so this topic's demo "
                        "runs the real thing. The arena's own request model "
                        "is the boundary discipline in miniature — the "
                        "model choice is a Literal (a bogus key is refused "
                        "before any arena code runs) and the candidates "
                        "arrive as deliberately raw JSON for the chosen "
                        "model to judge:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="why-boundary-request-code",
                    language="py",
                    caption="The arena's request model: choice constrained by Literal, candidates raw.",
                    source="server/guide/domain/demos/validation_arena.py",
                    snippet=(
                        "class ArenaRequest(CamelModel):\n"
                        "    \"\"\"One arena round: name a roster model, supply candidate field values.\n"
                        "\n"
                        "    ``candidates`` is deliberately raw JSON — whatever the caller believes\n"
                        "    the model's fields should carry, wire-spelled (camelCase), judged by the\n"
                        "    model itself. The Literal ``model`` is the boundary discipline in\n"
                        "    miniature: an unknown choice never reaches the builder.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    model: ArenaModelKey\n"
                        "    candidates: dict[str, JsonValue]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-boundary-coda",
                    text=(
                        "Notice what even this small model refuses to "
                        "promise: ``candidates`` is a dict of raw JSON "
                        "values, NOT a typed shape — because the whole "
                        "point of the demo is to watch what the target "
                        "model does with whatever arrived. Every other "
                        "model in this codebase points the other way: "
                        "declare the type, let the boundary enforce it. "
                        "The rest of this topic is about how much each "
                        "layer enforces, and what the enforcement looks "
                        "like on the wire when it fires."
                    ),
                ),
            ],
        ),
        # ── 2. The three layers of validation ──────────────────────────────
        Section(
            id="the-three-layers-of-validation",
            title="The three layers of validation",
            blocks=[
                TextBlock(
                    kind="text",
                    id="layers-pitch",
                    text=(
                        "\"Validate at the boundary\" is the slogan; the "
                        "practice is three layers with different jobs. "
                        "You have met all three already without the name — "
                        "this section just lines them up, because knowing "
                        "which layer a check belongs to is most of the "
                        "design skill this topic teaches:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="layers-list",
                    ordered=False,
                    items=[
                        "Edge validation — FastAPI + pydantic on the way "
                        "in: bodies, path variables, query parameters "
                        "parsed into typed models before a handler runs; "
                        "failure is the 422 envelope, automatically.",
                        "Domain validation — the rules a use case or store "
                        "defends itself, expressed on its own models: "
                        "invariants that must hold no matter who calls, "
                        "HTTP or not; failure is a typed AppError.",
                        "Composed validation — whole-object checks a "
                        "constructor runs once, fail-fast: the content "
                        "registry refusing to exist on a duplicate id, "
                        "config refusing to boot on a bad value.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="layers-edge-read",
                    text=(
                        "The edge layer is where FastAPI earns its keep: "
                        "you declare the model, the framework runs "
                        "pydantic's pipeline over the raw bytes, and a "
                        "failure never reaches your code — it becomes a "
                        "422 through one exception handler registered "
                        "once per app. Topic 08 met that registration as "
                        "a cross-cutting concern; here is the line that "
                        "owns this topic:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="layers-registration-code",
                    language="py",
                    caption="One registration per app: request validation failures get the shared envelope.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    add = app.add_exception_handler\n"
                        "    add(AppError, handle_app_error)  # type: ignore[arg-type]\n"
                        "    add(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="layers-domain-read",
                    text=(
                        "The domain layer exists because the edge only "
                        "guards the doors it knows about. A store that can "
                        "also be called from a script, a background job, or "
                        "another service cannot trust that whoever calls it "
                        "pre-validated anything — so it re-runs pydantic on "
                        "its own terms and raises its own typed error. The "
                        "scenario store is the repo's smallest honest "
                        "example: the PATCH body is edge-validated, but the "
                        "store still revalidates the merged state, because "
                        "patches can arrive from untyped callers too:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="layers-store-code",
                    language="py",
                    caption="The domain defends its own invariant — even against callers with no HTTP in sight.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "    def update(self, patch: ScenarioPatch) -> ScenarioState:\n"
                        "        \"\"\"Merge only the fields the patch set, revalidating the enums.\n"
                        "\n"
                        "        Raises ``AppError(validation_failed)`` if the merged state is not a\n"
                        "        legal ScenarioState — the store defends its own invariant because\n"
                        "        patches can also arrive from untyped callers, not just HTTP bodies\n"
                        "        (which FastAPI pre-validates).\n"
                        "        \"\"\"\n"
                        "        changes = patch.model_dump(exclude_unset=True)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="layers-division",
                    text=(
                        "The division of labor, stated once: the edge "
                        "validates the WIRE — shape, types, ranges, the "
                        "contract with the outside. The domain validates "
                        "INVARIANTS — truths that must hold regardless of "
                        "transport. Composed validation guards construction "
                        "— the registry's rule that content is valid or the "
                        "process does not start. When a check could live in "
                        "two layers, push it outward: every rule the edge "
                        "enforces is a rule no inner layer has to carry, "
                        "and every refusal the edge makes is a refusal with "
                        "a consistent, documented shape. The next section "
                        "is that shape."
                    ),
                ),
            ],
        ),
        # ── 3. pydantic at the edge — the 422 envelope (inline demo) ───────
        Section(
            id="pydantic-at-the-edge",
            title="pydantic at the edge — the 422 envelope",
            lead="The demo of this topic lives here — beside the teaching it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="edge-pitch",
                    text=(
                        "Watch what happens when a bad body arrives at any "
                        "endpoint of this server: the handler never runs. "
                        "FastAPI catches pydantic's "
                        "``RequestValidationError``, the shared handler "
                        "maps it onto the family "
                        "envelope, and the client gets 422 with one "
                        "``{loc, msg, type}`` triple per problem — the "
                        "location naming the field, the message human-"
                        "readable, the type a stable machine code like "
                        "``string_too_short`` or ``missing``. You met these "
                        "triples in topic 09's playground; here is the "
                        "code that produces them:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="edge-handler-code",
                    language="py",
                    caption="The handler behind every 422 this server serves.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "async def handle_request_validation_error(\n"
                        "    request: Request, exc: RequestValidationError\n"
                        ") -> JSONResponse:\n"
                        "    \"\"\"FastAPI body/path/query validation → 422 validation_failed envelope.\n"
                        "\n"
                        "    Pydantic's raw errors carry url/ctx noise; clients get the normalized\n"
                        "    ``{loc, msg, type}`` triples only.\n"
                        "    \"\"\"\n"
                        "    details = [\n"
                        "        {\"loc\": list(err[\"loc\"]), \"msg\": err[\"msg\"], \"type\": err[\"type\"]} for err in exc.errors()\n"
                        "    ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="edge-loc-read",
                    text=(
                        "The ``loc`` path deserves a slow read because it "
                        "is the triple's most useful part. It names WHERE "
                        "the failure was, as a path from the request: "
                        "``[\"body\", \"title\"]`` says the ``title`` field "
                        "of the request model failed; a bad path variable "
                        "(topic 07's ``{note_id}`` as ``not-a-number``) "
                        "reports ``[\"path\", \"note_id\"]``; a bad query "
                        "parameter would report ``[\"query\", ...]``. "
                        "Inside a body the path nests arbitrarily deep — "
                        "``[\"body\", \"tags\", 0]`` is the first tag — so "
                        "a client can point at the exact offending value "
                        "in its own UI. The type is deliberately stable "
                        "vocabulary (``string_too_short``, "
                        "``greater_than_equal``, ``literal_error``, "
                        "``missing``, ``value_error``): messages are for "
                        "humans and may be reworded; types are for code."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="edge-422-divergence",
                    text=(
                        "Why 422 and not 400? This is a deliberate "
                        "framework-idiom divergence inside the guide "
                        "family, recorded in the taxonomy itself. 400 Bad "
                        "Request is the generic \"you sent nonsense\"; "
                        "FastAPI's own idiom answers request-validation "
                        "failures with 422 Unprocessable Content, and "
                        "``RequestValidationError`` defaults there — the "
                        "express and spring boot siblings both map their "
                        "equivalent failure to 400, but a guide that "
                        "teaches FastAPI should speak FastAPI natively, "
                        "so the kind-to-status table follows the "
                        "framework and the divergence is taught, not "
                        "hidden:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="edge-decision-code",
                    language="py",
                    caption="The recorded decision: family envelope, framework-native status.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "Recorded family decisions:\n"
                        "- ``validation_failed`` → HTTP 422 (FastAPI-idiomatic; the express sibling\n"
                        "  uses 400 — deliberate divergence, taught in the validation topic)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="edge-arena-pitch",
                    text=(
                        "The demo makes all of this hands-on. It is an "
                        "arena of three REAL models this server validates "
                        "elsewhere — the notes playground's POST body "
                        "(topic 09), the pyd lab's strict specimen (topic "
                        "05), and the scenario PATCH — and you throw "
                        "candidate field values at your chosen contender. "
                        "The server runs the model's own pydantic "
                        "validation (not a simulation) and reports each "
                        "field as accepted, coerced (original → coerced "
                        "shown), or rejected with the exact ``loc``/``type``"
                        "/``msg`` triple the 422 envelope would carry. The "
                        "router is two thin routes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="edge-arena-router-code",
                    language="py",
                    caption="The arena's POST: parse the request model, call the pure builder.",
                    source="server/guide/presentation/routers/demo/validation.py",
                    snippet=(
                        "@router.post(\n"
                        "    \"/arena\", response_model=ArenaVerdictPayload, response_model_exclude_none=True\n"
                        ")\n"
                        "def run_arena(request: ArenaRequest) -> ArenaVerdictPayload:\n"
                        "    \"\"\"Judge one round: the chosen model's real validation over the candidates.\"\"\"\n"
                        "    return build_arena_verdict(request)"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="validation:arena",
                    title="The validation arena",
                    description=(
                        "Pick a real model from the roster, feed it "
                        "candidate field values, and watch pydantic "
                        "judge: accepted fields keep what you sent, "
                        "coerced fields show original → coerced (send "
                        "score as \"100\", count as \"3\", a handle with "
                        "padding and capitals), rejected fields carry the "
                        "exact {loc, msg, type} triple the 422 envelope "
                        "would report — string_too_short on an empty "
                        "title, less_than_equal on score 101, "
                        "literal_error on dataMode \"loud\", missing on a "
                        "required field you omitted, and value_error at "
                        "[\"body\"] when the lab specimen's cross-field "
                        "rule fires (flag with no tags). Unknown keys are "
                        "reported as ignored extras; a bogus model choice "
                        "never reaches the arena at all — the request "
                        "model's Literal is the edge refusing it for you."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="edge-arena-honesty",
                    text=(
                        "One honesty rule the arena enforces is worth "
                        "stealing as a habit: its error triples are "
                        "produced by normalizing the SAME pydantic errors "
                        "the envelope handler normalizes — including the "
                        "``body`` prefix FastAPI adds — so the demo and "
                        "the framework cannot drift apart. The builder "
                        "does the normalization once, next to the real "
                        "validation run:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="edge-arena-triples-code",
                    language="py",
                    caption="The arena reports the envelope's own triples — body-prefixed, normalized.",
                    source="server/guide/domain/demos/validation_arena.py",
                    snippet=(
                        "def _body_triples(errors: list[ErrorDetails]) -> list[ArenaError]:\n"
                        "    \"\"\"Normalize raw pydantic errors to the envelope's ``body``-prefixed triples.\n"
                        "\n"
                        "    Exactly what ``handle_request_validation_error`` does to a\n"
                        "    ``RequestValidationError`` — minus the url/ctx noise, with ``body``\n"
                        "    (the parameter location FastAPI reports for a request model) prepended.\n"
                        "    \"\"\"\n"
                        "    return [\n"
                        "        ArenaError(\n"
                        "            loc=[\"body\", *[str(part) for part in error[\"loc\"]]],\n"
                        "            msg=error[\"msg\"],\n"
                        "            type=error[\"type\"],\n"
                        "        )\n"
                        "        for error in errors\n"
                        "    ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="edge-coda",
                    text=(
                        "Two footnotes close the picture. First, the "
                        "envelope is the SAME one every failure gets — "
                        "code ``validation_failed``, a request id, the "
                        "x-request-id header — so a client's error "
                        "handling is uniform across 404s, 422s, and 500s "
                        "alike (topic 30 takes the whole taxonomy "
                        "deeper). Second, coercion failures and shape "
                        "failures answer identically: there is no "
                        "separate \"it wasn't even JSON\" path — a body "
                        "that does not parse, a field with the wrong "
                        "shape, and a field out of range all arrive as "
                        "triples in one envelope. That uniformity is why "
                        "clients can render validation errors "
                        "generically, field by field, without knowing "
                        "anything about the model that refused them."
                    ),
                ),
            ],
        ),
        # ── 4. Field constraints + Annotated ───────────────────────────────
        Section(
            id="field-constraints-and-annotated",
            title="Field constraints and Annotated",
            blocks=[
                TextBlock(
                    kind="text",
                    id="constraints-pitch",
                    text=(
                        "The cheapest validation is the kind you declare "
                        "instead of write: constraints are metadata on "
                        "the field, enforced by the same pipeline that "
                        "parses the type, surfaced in the OpenAPI schema "
                        "for free. The notes playground's body is the "
                        "canonical example in this repo — a title that "
                        "must exist (``min_length=1``) but not dominate "
                        "(``max_length=80``), plus two fields whose "
                        "validity is simply \"anything of the right "
                        "type, or absent\":"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="constraints-note-code",
                    language="py",
                    caption="Constraints declared where the contract is: on the field.",
                    source="server/guide/domain/demos/request_methods.py",
                    snippet=(
                        "class NoteCreate(CamelModel):\n"
                        "    \"\"\"The POST/PUT body: the full representation a client sends.\"\"\"\n"
                        "\n"
                        "    title: Annotated[str, Field(min_length=1, max_length=80)]\n"
                        "    body: str = \"\"\n"
                        "    tags: list[str] = []"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="constraints-annotated-read",
                    text=(
                        "Why ``Annotated[str, Field(...)]`` instead of "
                        "``str = Field(...)``? Both work in pydantic v2; "
                        "the Annotated form separates WHAT the value is "
                        "(the type) from WHAT MUST HOLD (the constraint), "
                        "and — the practical reason — an annotated TYPE "
                        "can be named once and reused. The pyd lab does "
                        "exactly that: its score bounds and its "
                        "canonicalizing handle are module-level "
                        "declarations, so the same rule binds the lab "
                        "model, the arena roster, and anything else that "
                        "wants it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="constraints-aliases-code",
                    language="py",
                    caption="Constraints as named types: declare once, bind anywhere.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "ScoreField = Annotated[int, Field(ge=1, le=100)]\n"
                        "\"\"\"The constrained target: coercion first, then the 1..100 bounds.\"\"\"\n"
                        "\n"
                        "HandleField = Annotated[str, AfterValidator(canonical_handle)]\n"
                        "\"\"\"The validator-as-type target: any string, then canonicalized.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="constraints-order",
                    text=(
                        "Note the order of operations those docstrings "
                        "record, because it explains every outcome you "
                        "can provoke in the arena: COERCION FIRST, THEN "
                        "THE BOUNDS. A score of ``\"100\"`` arrives as a "
                        "string, lax mode coerces it to 100, and only "
                        "then does ``le=100`` judge the integer — "
                        "accepted. A score of ``\"101\"`` becomes 101 and "
                        "fails ``less_than_equal``; a score of "
                        "``\"wide\"`` fails coercion itself with "
                        "``float_parsing``-style type errors. Constraint "
                        "and coercion are one pipeline, not two passes, "
                        "which is why the 422's type vocabulary covers "
                        "both without distinguishing them."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="constraints-vocabulary",
                    text=(
                        "The constraint vocabulary is broader than "
                        "lengths and ranges, and the roster's third model "
                        "shows the other half: vocabulary constraints. "
                        "``Literal`` enumerates the legal spellings, so "
                        "``dataMode: \"loud\"`` is as dead as a negative "
                        "id — with a crisper error (``literal_error`` "
                        "names the expected values). Optionality is "
                        "declared the same way, with a default; "
                        "``ScenarioPatch`` combines both so that a "
                        "missing key means \"unchanged\":"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="constraints-scenario-code",
                    language="py",
                    caption="Literal vocabulary + optional-with-default: the PATCH body.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "class ScenarioPatch(CamelModel):\n"
                        "    \"\"\"Partial update body for PATCH /api/demo/scenario.\n"
                        "\n"
                        "    Missing keys mean \"unchanged\" (never None-as-value) — the store merges\n"
                        "    with ``model_dump(exclude_unset=True)``.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    data_mode: DataMode | None = None\n"
                        "    inject_failure: FailureInjection | None = None"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="constraints-coda",
                    text=(
                        "The rule of thumb this repo follows: if a "
                        "constraint can be a ``Field(...)`` argument or a "
                        "``Literal``, it should be. Declared constraints "
                        "are enforced at every construction site, "
                        "documented in the generated schema, and "
                        "consistent by construction. The moment a rule "
                        "needs logic — depends on the value's shape, on "
                        "another field, on the outside world — metadata "
                        "stops being enough, and you graduate to the "
                        "next section's validators."
                    ),
                ),
            ],
        ),
        # ── 5. Custom validators ───────────────────────────────────────────
        Section(
            id="custom-validators",
            title="Custom validators",
            blocks=[
                TextBlock(
                    kind="text",
                    id="validators-pitch",
                    text=(
                        "Some rules refuse to be metadata. \"Normalize "
                        "this handle before storing it\", \"reject "
                        "reserved words\", \"require a tag list whose "
                        "items have no spaces\" — these need CODE, and "
                        "pydantic's answer is the ``@field_validator``: a "
                        "function that receives the field's post-coercion "
                        "value and returns the value the model will "
                        "actually hold. Return a transformed value and "
                        "the validator is a canonicalizer; raise "
                        "``ValueError`` and it is a gate. The lab's "
                        "handle rule is both at once — a real function, "
                        "written once:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-canonical-code",
                    language="py",
                    caption="The rule itself: pure function, one job, reusable everywhere.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "def canonical_handle(value: str) -> str:\n"
                        "    \"\"\"Canonical demo handle: lowercase, whitespace collapsed to hyphens.\"\"\"\n"
                        "    return \"-\".join(value.lower().split())"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-field-code",
                    language="py",
                    caption="Binding it: the decorator names the field; the function polices it.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "    @field_validator(\"handle\")\n"
                        "    @classmethod\n"
                        "    def canonicalize_handle(cls, value: str) -> str:\n"
                        "        \"\"\"Delegate to ``canonical_handle`` — one rule, reused by the report.\"\"\"\n"
                        "        return canonical_handle(value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validators-placement",
                    text=(
                        "Placement matters: a field validator runs AFTER "
                        "coercion and constraint checks for that field "
                        "(so your function sees a clean ``str``, never "
                        "the raw ``\" 42 \"`` a client may have sent for "
                        "a numeric field), and its failure reports with "
                        "the field's own ``loc`` and type "
                        "``value_error`` — you saw exactly that if you "
                        "pushed a handle-only problem through the lab or "
                        "the arena. The @classmethod-under-decorator "
                        "shape is the v2 idiom: the validator is looked "
                        "up on the class, works for subclasses, and "
                        "keeps the signature honest about receiving no "
                        "``self``."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validators-annotated-form",
                    text=(
                        "The lab also shows the OTHER way to bind a "
                        "validator — not by decorating the model, but by "
                        "attaching it to the type: "
                        "``HandleField = Annotated[str, "
                        "AfterValidator(canonical_handle)]``, quoted in "
                        "the previous section. ``AfterValidator`` wraps "
                        "any callable as post-validation metadata, so "
                        "the rule travels with the TYPE: any field "
                        "annotated ``HandleField`` gets canonicalization "
                        "without knowing the function's name. Decorate "
                        "the model when the rule is that model's "
                        "business; annotate the type when the rule is "
                        "the value's nature. In a codebase this small "
                        "the difference is taste; in a large one, "
                        "type-attached validators are how you build a "
                        "vocabulary of trusted scalars (``TagName``, "
                        "``Slug``, ``Email``) that every model shares."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validators-modes",
                    text=(
                        "For completeness: validators also run BEFORE "
                        "coercion — ``@field_validator(..., "
                        "mode=\"before\")`` and ``BeforeValidator`` see "
                        "the raw value exactly as it arrived, which is "
                        "the tool for inputs pydantic cannot coerce on "
                        "its own (dates in a house format, comma-"
                        "separated strings that should become lists). "
                        "This repo uses none, and that restraint is "
                        "deliberate: a before-validator opts out of the "
                        "coercion pipeline topic 05 walked through, so "
                        "it re-owns every safety the pipeline provided. "
                        "Reach for one only when the after-world "
                        "genuinely cannot express the rule, and keep "
                        "the function total — every input, including "
                        "``None`` and wrong types, must return or "
                        "raise, never crash."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validators-caution",
                    text=(
                        "Two cautions keep validators honest. First, "
                        "keep them PURE and CHEAP — no I/O, no clock, no "
                        "database lookups; a validator runs on every "
                        "construction, including reads in tests, and "
                        "anything slow or external belongs in a use case "
                        "where it can fail with a proper failure kind. "
                        "Second, prefer transformation to rejection "
                        "when both are defensible: canonicalizing "
                        "``\"  Grace Hopper \"`` to ``grace-hopper`` is "
                        "kind to clients and shrinks the error surface; "
                        "rejecting it teaches them nothing the coercion "
                        "didn't already fix. Reject what you cannot "
                        "canonicalize safely — that is the whole "
                        "decision."
                    ),
                ),
            ],
        ),
        # ── 6. Model-level / composed validation ───────────────────────────
        Section(
            id="model-level-and-composed-validation",
            title="Model-level and composed validation",
            blocks=[
                TextBlock(
                    kind="text",
                    id="model-pitch",
                    text=(
                        "The hardest rules span fields: \"a flagged "
                        "experiment needs at least one tag\", \"end must "
                        "be after start\", \"exactly one of these "
                        "identifiers\". No single field is wrong, so no "
                        "field validator can own the check — enter "
                        "``@model_validator``, which sees the WHOLE "
                        "constructed model. The lab specimen's rule is "
                        "the repo's real one, and the arena shows its "
                        "failure signature live — the error's loc is "
                        "just ``[\"body\"]``, the model itself:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="model-validator-code",
                    language="py",
                    caption="A cross-field rule: no single field is wrong; the combination is.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "    @model_validator(mode=\"after\")\n"
                        "    def flag_needs_tags(self) -> \"LabSpecimen\":\n"
                        "        \"\"\"Cross-field rule: an enabled experiment carries at least one tag.\"\"\"\n"
                        "        if self.flag and not self.tags:\n"
                        "            raise ValueError(\"flag requires at least one tag\")\n"
                        "        return self"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="model-order-read",
                    text=(
                        "``mode=\"after\"`` is the mode you want by "
                        "default: the validator receives a fully built, "
                        "field-validated instance, so it never has to "
                        "re-check types — if ANY field failed, the model "
                        "validator does not run at all, and the 422 "
                        "carries only the field errors. That ordering is "
                        "why the arena's cross-field round (flag with no "
                        "tags) shows every field accepted while the "
                        "verdict is still rejected: the fields passed, "
                        "the composition failed. An ``after`` model "
                        "validator must return the instance — returning "
                        "``self`` unchanged is the norm, but it may also "
                        "repair, which makes model validators the right "
                        "home for derivations that must never be absent "
                        "(\"default the slug from the title\")."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="model-composed-pitch",
                    text=(
                        "Beyond pydantic sits composed validation — "
                        "checks that are less about one model's fields "
                        "and more about a whole population or "
                        "configuration being coherent. This repo's "
                        "flagship is the content registry: at "
                        "construction it runs every rule (unique topic "
                        "ids, unique section ids, valid demo ids, "
                        "sourced snippets) and REFUSES TO EXIST "
                        "otherwise, so broken content kills the process "
                        "at startup instead of rendering half a guide "
                        "at request time. Fail-fast construction is "
                        "validation's strongest form — nothing invalid "
                        "ever gets the chance to accumulate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="model-registry-code",
                    language="py",
                    caption="Composed validation: the registry runs every rule before it exists.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "def _validate(topics: Sequence[Topic], groups: Sequence[TopicGroup]) -> None:\n"
                        "    \"\"\"Run every rule; raise RegistryError on the first violation.\"\"\"\n"
                        "    known_group_ids = {group.id for group in groups}\n"
                        "\n"
                        "    seen_topic_ids: set[str] = set()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="model-when-not-pydantic",
                    text=(
                        "When should composed checks be hand-rolled "
                        "instead of a giant model validator? The "
                        "registry's reasons generalize. Its rules span "
                        "MANY objects (uniqueness across topics), need "
                        "external context (the group list), and must "
                        "fail with actionable, rule-naming messages — "
                        "each a signal the check has outgrown a single "
                        "model's declaration. The scenario store shows "
                        "the middle ground: it re-runs pydantic on the "
                        "MERGED state (a model check), but wraps the "
                        "failure in the app's own typed error (a "
                        "composed decision), because its callers "
                        "deserve the envelope, not a pydantic traceback. "
                        "Rule of thumb: pydantic for everything about "
                        "one model's values; typed, rule-naming checks "
                        "for everything about populations, "
                        "configurations, and sequences of operations."
                    ),
                ),
            ],
        ),
        # ── 7. Choosing an approach ────────────────────────────────────────
        Section(
            id="choosing-an-approach",
            title="Choosing an approach",
            blocks=[
                TextBlock(
                    kind="text",
                    id="choosing-pitch",
                    text=(
                        "The sections above handed you four escalation "
                        "levels — declared constraints, custom field "
                        "validators, model validators, composed checks — "
                        "and the choice is usually made for you if you "
                        "ask the right question of the rule. The "
                        "decision table this repo actually follows:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="choosing-list",
                    ordered=False,
                    items=[
                        "Type — the field must BE something: annotate "
                        "the type (str, int, list[str], Literal); "
                        "coercion and type errors come free.",
                        "Range or shape of one field — bounds, lengths, "
                        "patterns: Field(...) constraints, ideally as a "
                        "named Annotated type for reuse.",
                        "One field needs logic — normalize or gate a "
                        "single value: @field_validator (or "
                        "AfterValidator on the type when the rule is "
                        "the value's nature).",
                        "Fields combine into a rule — start/end, "
                        "exactly-one-of, cross-field invariants: "
                        "@model_validator(mode=\"after\").",
                        "Many objects or the configuration must be "
                        "coherent — uniqueness, referential integrity, "
                        "boot-time safety: hand-rolled fail-fast "
                        "checks raising typed errors.",
                        "The rule needs I/O — checking against a "
                        "database or an external service: NOT a "
                        "validator at all; a use case that fails with a "
                        "domain failure kind.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="choosing-depth",
                    text=(
                        "One more axis: how much validation is TOO "
                        "much at the edge? The answer is drawn by what "
                        "downstream layers assume. This server's "
                        "contracts promise \"everything inside the "
                        "boundary matches its declared type and "
                        "constraints\" — so the edge owns shape, type, "
                        "range, and vocabulary, and handlers can index, "
                        "slice, and compare without ceremony. The edge "
                        "does NOT own existence (that 404 is a domain "
                        "answer, as topic 09's notes showed), "
                        "authorization (topic 24), or any truth that "
                        "needs I/O. Pushing those into a validator would "
                        "make the 422 lie — \"unprocessable\" would then "
                        "mean \"filed under the wrong user\", and "
                        "clients would be wrong to render it field by "
                        "field. The status code is part of the "
                        "contract; spend it honestly."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="choosing-coda",
                    text=(
                        "And the pragmatic closer: validation is a "
                        "place where DONE beats PERFECT. A declared "
                        "``min_length=1`` that ships today catches more "
                        "real garbage than an exhaustive rule set that "
                        "ships next quarter; every triple in a 422 is a "
                        "bug report a client can fix without your logs. "
                        "Start with types and constraints, add "
                        "validators where real inputs misbehave, and "
                        "let the envelope do the talking. The curl tour "
                        "below lets you watch every layer of that "
                        "ladder fire, on purpose, from a terminal."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="choosing-testing",
                    text=(
                        "One testing note, because validation is the "
                        "most testable layer you own: every rule "
                        "declared in this topic is pinned by a test "
                        "that asserts the exact wire shape — the arena "
                        "endpoint's tests check a rejected score's "
                        "``[\"body\", \"score\"]`` loc and "
                        "``less_than_equal`` type, the bogus-model-key "
                        "test checks the edge's own "
                        "``[\"body\", \"model\"]`` literal_error triple, "
                        "and the content tests pin this very section "
                        "list. That is the standard worth copying: do "
                        "not merely assert ``status_code == 422`` — pin "
                        "the loc, the type, and the envelope keys, "
                        "because those ARE the client-facing contract. "
                        "A validation rule without a shape-pinning test "
                        "is a contract nobody enforces."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Every refusal in this topic, provoked on purpose and read off the wire.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour "
                        "walks the arena through all three outcomes and "
                        "then provokes the edge's own 422s — including "
                        "the one the arena's request model throws for a "
                        "bogus roster choice. -i shows the status lines; "
                        "python3 -m json.tool keeps it dependency-free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-roster",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the roster: three real models and their field rules\n"
                        "curl -s localhost:8000/api/demo/validation/arena/roster | python3 -m json.tool | head -40"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-accept",
                    language="bash",
                    source=None,
                    snippet=(
                        "# accepted: every field passes, absent fields default\n"
                        "curl -s -X POST localhost:8000/api/demo/validation/arena -H 'content-type: application/json' \\\n"
                        "  -d '{\"model\":\"note-create\",\"candidates\":{\"title\":\"from the tour\",\"tags\":[\"terminal\"]}}' | python3 -m json.tool | head -30"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-coerce",
                    language="bash",
                    source=None,
                    snippet=(
                        "# coerced: \"3\"→3, \"true\"→true, padded handle → canonical\n"
                        "curl -s -X POST localhost:8000/api/demo/validation/arena -H 'content-type: application/json' \\\n"
                        "  -d '{\"model\":\"lab-specimen\",\"candidates\":{\"count\":\"3\",\"flag\":\"true\",\"tags\":[\"terminal\"],\"score\":\"100\",\"handle\":\"  Validation Arena \"}}' \\\n"
                        "  | python3 -m json.tool | grep -A6 '\"outcome\"' | head -28"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-reject",
                    language="bash",
                    source=None,
                    snippet=(
                        "# rejected: score 101 + the exact envelope triples (loc, type, msg)\n"
                        "curl -s -X POST localhost:8000/api/demo/validation/arena -H 'content-type: application/json' \\\n"
                        "  -d '{\"model\":\"lab-specimen\",\"candidates\":{\"count\":1,\"flag\":true,\"tags\":[\"t\"],\"score\":101,\"handle\":\"x\"}}' \\\n"
                        "  | python3 -m json.tool | grep -A4 '\"errors\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-cross-field",
                    language="bash",
                    source=None,
                    snippet=(
                        "# cross-field: every field accepted, the MODEL refuses — loc is just [\"body\"]\n"
                        "curl -s -X POST localhost:8000/api/demo/validation/arena -H 'content-type: application/json' \\\n"
                        "  -d '{\"model\":\"lab-specimen\",\"candidates\":{\"count\":1,\"flag\":true,\"tags\":[],\"score\":5,\"handle\":\"x\"}}' \\\n"
                        "  | python3 -m json.tool | grep -B1 -A5 '\"verdict\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-bogus-model",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the edge's own 422: a bogus model key dies before the arena runs\n"
                        "curl -s -i -X POST localhost:8000/api/demo/validation/arena -H 'content-type: application/json' \\\n"
                        "  -d '{\"model\":\"does-not-exist\",\"candidates\":{}}'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-scenario",
                    language="bash",
                    source=None,
                    snippet=(
                        "# literal vocabulary elsewhere: a bad enum against the scenario PATCH\n"
                        "curl -s -i -X PATCH localhost:8000/api/demo/scenario -H 'content-type: application/json' -d '{\"dataMode\":\"loud\"}'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Read the bogus-model answer closely and you "
                        "have the whole topic in one response: status "
                        "422 (FastAPI's idiom, the deliberate family "
                        "divergence), the shared envelope with code "
                        "validation_failed and a request id, and a "
                        "details triple whose loc — [\"body\", "
                        "\"model\"] — names exactly the field that "
                        "failed, with type literal_error naming exactly "
                        "how. That is the contract this server offers "
                        "every client: refuse early, refuse precisely, "
                        "and refuse in a shape code can consume. The "
                        "Request handling group is complete — topic 11 "
                        "turns to designing whole APIs on top of these "
                        "mechanics."
                    ),
                ),
            ],
        ),
    ],
)
