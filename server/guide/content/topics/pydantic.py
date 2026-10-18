"""Topic 05 — pydantic: the validation engine at this guide's boundary.

Pydantic taught from the one codebase that is literally made of it: why
models belong at the boundary · BaseModel + Field · the validation pipeline
and its lax coercion rules (measured, not folklore) · validators escalating
from Annotated types to @field_validator to @model_validator · serialization
and the camelCase/exclude-none wire conventions · nested models and the
discriminated union that carries this very page · pydantic-settings · the
pydantic-core engine and JSON Schema generation — with the topic's
validation-laboratory demo INLINE, and the terminal companion closing.

Every code block below quotes a real repo file (the snippet ratchet
verifies it); bash blocks are the sourcing-exempt exception. The demo
builder in guide/domain/demos/pyd_lab.py is the real home of this repo's
first @field_validator, @model_validator, constrained Annotated field, and
TypeAdapter usage — written for this topic, quoted from the file.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="pydantic",
    title="Pydantic, the boundary",
    subtitle=(
        "The validation and serialization engine under every request this "
        "server accepts and every response it emits — taught from the guide's "
        "own models, with a live lab that shows coercion deciding."
    ),
    group="framework",
    order=5,
    sections=[
        # ── 1. Why models at the boundary ───────────────────────────────────
        Section(
            id="why-models-at-the-boundary",
            title="Why models at the boundary",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-pitch",
                    text=(
                        "Every web backend answers one question thousands of "
                        "times a day: is this input what I think it is? The "
                        "untyped answer is to trust the JSON parser and sprinkle "
                        "isinstance checks through the codebase — defensive code "
                        "that runs too late, in the wrong layer, and never "
                        "everywhere. The typed answer is to make the boundary "
                        "itself the type declaration: describe the shape you "
                        "accept, in one place, and let every byte crossing the "
                        "edge be checked against it before any business code "
                        "runs. FastAPI's deepest design choice is that this "
                        "description language is pydantic — a plain Python class "
                        "with type-hinted fields, so the same declaration gives "
                        "you runtime validation, static checking, editor "
                        "completion, and the generated OpenAPI schema. You "
                        "already know this from topic 04's anatomy lesson; this "
                        "topic is the engine underneath it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-this-guide",
                    text=(
                        "The honest case study is the page you are reading. "
                        "This guide's entire content engine is pydantic: each "
                        "topic is a Topic model, each teaching unit a Section, "
                        "every paragraph and code sample and demo pointer a "
                        "block in a discriminated union — and GET "
                        "/api/content/pydantic serializes exactly those models "
                        "to your browser. The declaration is short enough to "
                        "read in full, and every property the API promises "
                        "falls out of it: the field types, the Optional "
                        "subtitle (present or absent, never null), the ordered "
                        "lists, and the fail-fast startup that refuses to boot "
                        "on structurally broken content — because the registry "
                        "that holds these models validates them once at import "
                        "time, so a malformed topic can never reach a reader. "
                        "One class hierarchy is simultaneously documentation, "
                        "wire contract, and runtime guard:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="why-content-model",
                    language="py",
                    caption="The guide's own spine: Topic → Section → blocks, as pydantic models.",
                    source="server/guide/content/models.py",
                    snippet=(
                        "class Section(CamelModel):\n"
                        "    \"\"\"One teaching unit inside a topic: prose + code + its inline demo.\"\"\"\n"
                        "\n"
                        "    id: str\n"
                        "    title: str\n"
                        "    lead: str | None = None\n"
                        "    blocks: list[ContentBlock]\n"
                        "\n"
                        "\n"
                        "class Topic(CamelModel):\n"
                        "    \"\"\"A whole guide page: ordered sections, the unit the detail route serves.\"\"\"\n"
                        "\n"
                        "    id: str\n"
                        "    title: str\n"
                        "    subtitle: str | None = None\n"
                        "    group: str\n"
                        "    order: int\n"
                        "    sections: list[Section]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-coda",
                    text=(
                        "Notice what is absent: no from_json functions, no "
                        "manual key checking, no drift between what the server "
                        "validates and what it serves. The client's DTO layer "
                        "re-validates the same contract from its side (defense "
                        "in depth — the family convention), but the server's "
                        "half is one declaration. That is the argument for "
                        "models at the boundary in a sentence: state the "
                        "contract once, at the edge, in a language both the "
                        "type checker and the runtime understand. The rest of "
                        "this topic takes that declaration apart — the base "
                        "class and field constraints, the pipeline a value "
                        "travels through, the validators you attach when types "
                        "alone cannot decide, the serialization back out, and "
                        "the engine that makes it fast."
                    ),
                ),
            ],
        ),
        # ── 2. BaseModel + Field ────────────────────────────────────────────
        Section(
            id="basemodel-and-field",
            title="BaseModel and Field",
            blocks=[
                TextBlock(
                    kind="text",
                    id="base-pitch",
                    text=(
                        "A pydantic model is any class deriving from BaseModel "
                        "whose fields are plain type annotations. Instantiation "
                        "validates: Topic(id=123, ...) is refused at "
                        "construction (you watched exactly that rejection in "
                        "the python-language demo's boundary check — "
                        "string_type, because pydantic v2 does not coerce an "
                        "int into a str). Fields may carry a Field(...) "
                        "declaration for everything the annotation cannot say: "
                        "defaults, numeric bounds, string lengths, descriptions "
                        "that flow into the JSON Schema. Field is also how you "
                        "declare a discriminated union's tag (the content "
                        "model's Field(discriminator=\"kind\") — section 6 "
                        "takes that apart) and per-field serialization "
                        "behavior. This repo's most concentrated Field usage "
                        "lives in the validation lab this topic carries: a "
                        "constrained integer whose bounds ride the annotation, "
                        "so the constraint travels with the type wherever it "
                        "goes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="base-score-field",
                    language="py",
                    caption="Constraints as part of the type — not code in a handler.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "ScoreField = Annotated[int, Field(ge=1, le=100)]\n"
                        "\"\"\"The constrained target: coercion first, then the 1..100 bounds.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="base-config",
                    text=(
                        "The other half of the foundation is model_config — "
                        "class-level behavior for every model that shares a "
                        "base. This guide defines exactly one such base, "
                        "CamelModel, and every wire model in the server derives "
                        "from it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="camel-model-config-list",
                    ordered=False,
                    items=[
                        "alias_generator — Python stays snake_case while the wire "
                        "is camelCase.",
                        "populate_by_name — parsing accepts BOTH spellings, so "
                        "internal callers can construct models with Python names "
                        "while HTTP clients send camelCase.",
                        "frozen — instances are immutable snapshots, never mutated "
                        "in place, which also makes them hashable and safe to "
                        "share.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="base-config-lead",
                    text=(
                        "Three lines of configuration, inherited by dozens of "
                        "models, defining the whole server's serialization "
                        "accent:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="base-camel-model",
                    language="py",
                    caption="The base every wire model in this server shares.",
                    source="server/guide/core/serialization.py",
                    snippet=(
                        "class CamelModel(BaseModel):\n"
                        "    \"\"\"Base for every wire model: camelCase aliases, both-direction parsing, frozen.\"\"\"\n"
                        "\n"
                        "    model_config = ConfigDict(\n"
                        "        alias_generator=to_camel,\n"
                        "        populate_by_name=True,\n"
                        "        frozen=True,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="base-coda",
                    text=(
                        "The design lesson in CamelModel is bigger than casing: "
                        "cross-cutting wire rules belong in ONE base, not "
                        "repeated in every model. When the day comes that a "
                        "response needs different behavior — streaming "
                        "excludes some fields, an internal model is not frozen "
                        "— you derive a second base and say why, instead of "
                        "editing fifty classes. BaseModel gives you that lever; "
                        "plain dicts give you nothing to hold it with. With the "
                        "declaration vocabulary set, the next question is what "
                        "actually happens when a value meets these "
                        "declarations — the pipeline, and its most "
                        "consequential habit: coercion."
                    ),
                ),
            ],
        ),
        # ── 3. The validation pipeline + coercion ───────────────────────────
        Section(
            id="the-validation-pipeline",
            title="The validation pipeline and its coercion",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pipeline-steps",
                    text=(
                        "When FastAPI parses a JSON body into your model — "
                        "or when you call model_validate yourself — every "
                        "field walks the same pipeline:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="pipeline-stages-list",
                    ordered=True,
                    items=[
                        "Type match — the raw value is matched against the "
                        "annotation's type, in pydantic v2's default lax mode, "
                        "which COERCES near-miss values before rejecting them.",
                        "Field constraints — ge, le, min_length... run.",
                        "Custom validators — next section.",
                        "Model construction — frozen, in this repo's case.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-coercion",
                    text=(
                        "The coercion rules are "
                        "specific, and worth knowing exactly rather than "
                        "folklorically. This guide verified them against "
                        "pydantic 2.14 before writing them down:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="lax-coercion-rules-list",
                    ordered=False,
                    items=[
                        "A numeric string becomes the number — \"42\" → 42, even "
                        "with surrounding whitespace.",
                        "A whole float becomes the int — 4.0 → 4.",
                        "The boolean spellings \"true\"/\"on\"/\"yes\"/\"1\" "
                        "(case-insensitive, with their false counterparts) become "
                        "bool.",
                        "Sequences coerce across shapes — a tuple validates into "
                        "a list[str] field.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-refusals",
                    text=(
                        "The refusals are just as precise, and they are where "
                        "misconceptions live:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="coercion-refusals-list",
                    ordered=False,
                    items=[
                        "An int for a str field is rejected with string_type — "
                        "pydantic v2 does NOT coerce numbers into strings; the "
                        "strictest default in the whole pipeline, chosen because "
                        "silent 42 → \"42\" corrupts data in ways nobody notices.",
                        "A fractional value for an int field is refused — 4.5 "
                        "the float with int_from_float, \"4.5\" the string "
                        "with int_parsing.",
                        "A bool field refuses anything outside the recognized "
                        "spellings with bool_parsing — \"maybe\" never becomes "
                        "True.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-taxonomy",
                    text=(
                        "These type strings "
                        "are not decoration; they are pydantic's error "
                        "taxonomy, stable across versions, and the reason a "
                        "client can render a helpful message without parsing "
                        "English. And when you genuinely want no coercion at "
                        "all, strict=True is a mode away: "
                        "model_validate(payload, strict=True) rejects \"42\" "
                        "for an int field with int_type, because in strict "
                        "mode the JSON type must already be the Python type. "
                        "Lax at the HTTP edge (be liberal with honest "
                        "clients), strict between internal services (be "
                        "exact with your own code) is a defensible split — "
                        "this guide uses lax everywhere, because every "
                        "boundary it owns is typed on both sides."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-422",
                    text=(
                        "So where does FastAPI's famous 422 come from? When a "
                        "request body fails the pipeline, FastAPI raises "
                        "RequestValidationError carrying pydantic's raw "
                        "errors — which include learning-portal URLs and "
                        "context dicts that no API should leak verbatim. This "
                        "server registers a handler that normalizes each "
                        "error to exactly three keys — loc (the path to the "
                        "field, nested indexes and all), msg, and type — and "
                        "answers with the guide's standard error envelope. "
                        "You have hit this handler from curl since topic 01; "
                        "now you can read its source, and it is short because "
                        "pydantic already did the hard part:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-handler",
                    language="py",
                    caption="The real 422 path: normalize pydantic's errors, log, envelope.",
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
                        "    ]\n"
                        "    logger.info(\n"
                        "        \"request_validation_failed\",\n"
                        "        request_id=resolve_request_id(request),\n"
                        "        detail_count=len(details),\n"
                        "    )\n"
                        "    return _build_error_response(\n"
                        "        request,\n"
                        "        422,\n"
                        "        FailureKind.VALIDATION_FAILED,\n"
                        "        \"Request validation failed.\",\n"
                        "        details,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-coda",
                    text=(
                        "Read the detail line as the whole philosophy: the "
                        "handler trusts pydantic's structured errors, keeps "
                        "only what clients need, and hands them to the same "
                        "envelope builder every other failure uses (with the "
                        "request id, so the rejection is correlatable in "
                        "logs). Validation failure is not an exception to "
                        "apologize for — it is a first-class response the "
                        "system designed for. The lab demo at the end of this "
                        "topic lets you drive both sides of the pipeline "
                        "deliberately: bodies that coerce, bodies that "
                        "constrain-fail, and bodies that never get past the "
                        "request model at all."
                    ),
                ),
            ],
        ),
        # ── 4. Validators ───────────────────────────────────────────────────
        Section(
            id="validators",
            title="Validators: Annotated types, @field_validator, @model_validator",
            blocks=[
                TextBlock(
                    kind="text",
                    id="validators-ladder",
                    text=(
                        "Types and Field constraints decide most fields, but "
                        "some rules need code. Pydantic v2 offers a ladder of "
                        "three escalation levels, and the rule of thumb is to "
                        "stay as low as possible. Level one: an Annotated "
                        "type — wrap the constraint or transform in the type "
                        "itself, so it is reusable and travels with the "
                        "annotation. The validation lab uses this twice, once "
                        "for bounds (section 2's ScoreField) and once for a "
                        "normalizing validator composed onto a plain str — "
                        "AfterValidator runs your function after type "
                        "validation passes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-annotated",
                    language="py",
                    caption="Level one: the validator IS the type.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "def canonical_handle(value: str) -> str:\n"
                        "    \"\"\"Canonical demo handle: lowercase, whitespace collapsed to hyphens.\"\"\"\n"
                        "    return \"-\".join(value.lower().split())"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-handle-field",
                    language="py",
                    caption="Annotated + AfterValidator: any string, then canonicalized.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "HandleField = Annotated[str, AfterValidator(canonical_handle)]\n"
                        "\"\"\"The validator-as-type target: any string, then canonicalized.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validators-field",
                    text=(
                        "Level two: @field_validator — a method on the model, "
                        "chosen when the rule belongs to THIS model's field "
                        "rather than to a reusable type. It runs after "
                        "pydantic's own validation of the field (mode "
                        "\"after\"), receives the already-coerced value, and "
                        "returns the value to store — transforming, or "
                        "raising ValueError to reject with a message that "
                        "becomes the error's msg. (A mode=\"before\" "
                        "validator sees the RAW input instead — useful when "
                        "you must pre-shape untrusted spellings.) The lab's "
                        "specimen model declares one for real, delegating to "
                        "the same pure function the Annotated type uses — one "
                        "rule, two attachment points, no duplication:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-field-quote",
                    language="py",
                    caption="Level two: the repo's real @field_validator.",
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
                    id="validators-model",
                    text=(
                        "Level three: @model_validator — for rules no single "
                        "field can express, because they span fields. "
                        "mode=\"after\" runs once the whole model is built "
                        "and every field has passed; raise ValueError and the "
                        "rejection lands with an empty loc (it is the MODEL "
                        "that is wrong, not a field). The lab's specimen "
                        "carries a real one, and it is the demo's best "
                        "surprise: a submission can pass every per-field "
                        "check — count coerced, flag a real bool, tags a "
                        "list, score in bounds, handle canonical — and still "
                        "be refused, because the rule relates two fields:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-model-quote",
                    language="py",
                    caption="Level three: a cross-field rule, really enforced.",
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
                    id="validators-literal",
                    text=(
                        "A sibling worth naming: enum-like closed sets. When "
                        "a field admits exactly a handful of spellings, a "
                        "Literal type is validation without any code — the "
                        "type IS the whitelist, any other value is rejected "
                        "with a literal_error, and the generated JSON Schema "
                        "carries the allowed values into OpenAPI so clients "
                        "can render a dropdown. This repo's runtime scenario "
                        "toggle is exactly that shape, and the store that "
                        "owns it re-runs model_validate on every merged "
                        "patch precisely because the enum invariant is worth "
                        "defending even against untyped internal callers:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validators-literal-quote",
                    language="py",
                    caption="Literal types: the enum validation this repo actually runs on.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "DataMode = Literal[\"fake\", \"live\"]\n"
                        "FailureInjection = Literal[\"none\", \"error\", \"latency\"]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validators-coda",
                    text=("Where each level wins:"),
                ),
                ListBlock(
                    kind="list",
                    id="validators-levels-list",
                    ordered=False,
                    items=[
                        "Annotated types — for rules you would reuse or compose "
                        "(constraints, normalizations, well-known shapes).",
                        "@field_validator — for one model's field semantics.",
                        "@model_validator — for invariants across fields.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="validators-discipline",
                    text=(
                        "And a discipline worth "
                        "keeping: validators should be pure and cheap — they "
                        "run on every parse, including your test fixtures', "
                        "so database lookups and network calls do not belong "
                        "here (those are use-case work; the model checks "
                        "shape, not existence)."
                    ),
                ),
            ],
        ),
        # ── 5. Serialization ────────────────────────────────────────────────
        Section(
            id="serialization",
            title="Serialization: model_dump and the wire",
            blocks=[
                TextBlock(
                    kind="text",
                    id="serialize-pitch",
                    text=(
                        "Validation is half the boundary's job; the other "
                        "half is going back out. model_dump() turns a model "
                        "into a dict, and its arguments are the whole wire "
                        "vocabulary:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dump-arguments-list",
                    ordered=False,
                    items=[
                        "by_alias — True on this server: the camelCase spellings "
                        "CamelModel generates.",
                        "mode — \"json\": values JSON-serialize safely — "
                        "datetimes to ISO strings, UUIDs to text, enums to "
                        "values.",
                        "exclude_none — this guide treats it as a contract, not "
                        "a preference.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="serialize-none-contract",
                    text=(
                        "The family convention is that "
                        "absent facts are OMITTED, never sent as null — the "
                        "client's DTO validators treat null as invalid and "
                        "absent as fine, so a null on the wire is a bug "
                        "found at someone else's layer. The single most "
                        "load-bearing dump call in this server is inside the "
                        "error envelope builder — every failure response this "
                        "API has ever produced went through this exact line:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="serialize-dump",
                    language="py",
                    caption="The envelope's dump: json-mode, aliased, null-free.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    body = ErrorResponse(\n"
                        "        error=ErrorBody(code=kind.value, message=message, request_id=request_id, details=details)\n"
                        "    )\n"
                        "    headers = {\"x-request-id\": request_id}\n"
                        "    if extra_headers:\n"
                        "        headers.update(extra_headers)\n"
                        "    return JSONResponse(\n"
                        "        status_code=status,\n"
                        "        content=body.model_dump(mode=\"json\", by_alias=True, exclude_none=True),\n"
                        "        headers=headers,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="serialize-router",
                    text=(
                        "When FastAPI serializes a response_model for you, "
                        "the same knobs are route decorators instead: "
                        "response_model_exclude_none on the echo router "
                        "keeps a GET's \"no body facts\" honest — the keys "
                        "simply do not appear. There is also "
                        "model_dump_json() (the same dump, straight to a "
                        "JSON string, and the fastest path pydantic offers "
                        "for whole documents — the streaming demo used it "
                        "per NDJSON line), plus per-call surgical forms: "
                        "model_dump(include=..., exclude=...) for projections "
                        "and exclude_unset for PATCH semantics — the "
                        "scenario store's merge is exactly that trick, "
                        "\"the fields the request actually set\", "
                        "distinguishing an absent key from an explicit null "
                        "or default. Round-tripping is the mental model to "
                        "keep: model_validate is the inverse of "
                        "model_dump(mode=\"json\", by_alias=True) — the lab "
                        "depends on it, re-validating its raw request dump "
                        "into the strict specimen. One declaration, two "
                        "directions, zero glue code:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="serialize-exclude-none",
                    language="py",
                    caption="The router-level form of the same convention.",
                    source="server/guide/presentation/routers/demo/http.py",
                    snippet=(
                        "@router.post(\n"
                        "    \"/headers\", response_model=HttpHeadersEchoPayload, response_model_exclude_none=True\n"
                        ")"
                    ),
                ),
            ],
        ),
        # ── 6. Nested models and generics ───────────────────────────────────
        Section(
            id="nested-models-and-generics",
            title="Nested models, discriminated unions, and generics",
            blocks=[
                TextBlock(
                    kind="text",
                    id="nested-pitch",
                    text=(
                        "Real payloads nest, and pydantic validates trees "
                        "bottom-up with the same rules at every level: a "
                        "nested model field validates its own subtree, errors "
                        "carry the full path in loc (body → items → 3 → "
                        "quantity — you saw inner-loc errors in the pipeline "
                        "section's handler), and a child's failure rejects "
                        "the parent. The guide's content tree is the flagship "
                        "example: a Topic holds Sections, a Section holds "
                        "blocks — and the blocks are three DIFFERENT shapes "
                        "that must never be confused with each other. That "
                        "last requirement is the discriminated union, "
                        "pydantic's most underused powerful feature: each "
                        "variant carries a Literal tag field, one "
                        "Field(discriminator=...) names the tag, and parsing "
                        "dispatches on that key — no trial-and-error across "
                        "the union, and an unknown kind is rejected "
                        "immediately with the OFFENDING VALUE named, instead "
                        "of three confusing maybe-errors. The union that "
                        "renders this very page:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nested-discriminated",
                    language="py",
                    caption="The content model's discriminated union, in full.",
                    source="server/guide/content/models.py",
                    snippet=(
                        "class DemoBlock(CamelModel):\n"
                        "    \"\"\"Names a client-side live demo bound to real server endpoints.\n"
                        "\n"
                        "    The block id doubles as the demo id (``<area>:<name>``, e.g.\n"
                        "    ``runtime:async``) — the client's lookup key, validated by the registry.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    kind: Literal[\"demo\"]\n"
                        "    id: str\n"
                        "    title: str\n"
                        "    description: str | None = None\n"
                        "\n"
                        "\n"
                        "ContentBlock = Annotated[TextBlock | CodeBlock | DemoBlock | ListBlock, Field(discriminator=\"kind\")]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nested-why",
                    text=(
                        "Read what the discriminator buys: the client's "
                        "renderer switches on kind and gets exhaustive "
                        "narrowing; the registry's validator can check demo "
                        "block ids knowing exactly which blocks are demos; "
                        "and adding a fourth block type later means writing "
                        "one model with kind: Literal[\"quiz\"] and the "
                        "union's error message updates itself. Without the "
                        "discriminator, a union of similar models degrades "
                        "into best-guess matching (pydantic's smart mode "
                        "tries left to right) — workable for two distant "
                        "shapes, misleading for three near ones. The pattern "
                        "recurs wherever heterogeneous things ride one list: "
                        "event payloads, webhook envelopes, API result "
                        "variants — and this topic's lab uses it a second "
                        "time for its per-field outcomes (clean / coerced / "
                        "rejected, discriminated on status)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nested-generics",
                    text=(
                        "Generics are the other scaling axis. A generic "
                        "page-wrapper or envelope written once as "
                        "Page[T] validates any item type later, and "
                        "pydantic's tooling for using types as VALUES is "
                        "TypeAdapter: wrap any annotation — a bare int, a "
                        "constrained Annotated type, a nested list — and "
                        "validate or serialize standalone values against it "
                        "without inventing a one-field model. The lab builds "
                        "its entire report that way: one table mapping each "
                        "field to the rule it teaches and a TypeAdapter of "
                        "that field's strict target, so the demo validates "
                        "single fields with exactly the engine a model field "
                        "would use. (pydantic also ships create_model for "
                        "building model classes dynamically at runtime — "
                        "genuinely useful for config-driven schemas, and "
                        "genuinely avoidable in application code, where a "
                        "class you can jump-to-definition beats one built "
                        "from a dict.)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nested-typeadapter",
                    language="py",
                    caption="TypeAdapter: types as values — the lab's whole engine.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "_TARGETS: Final[dict[str, tuple[str, TypeAdapter[Any]]]] = {\n"
                        "    \"count\": (\"int — numeric strings and whole floats coerce, lax mode\", TypeAdapter(int)),\n"
                        "    \"flag\": ('bool — \"true\"/\"on\"/1/0 coerce; arbitrary strings do not', TypeAdapter(bool)),\n"
                        "    \"tags\": (\"list[str] — any sequence coerces, items must be strings\", TypeAdapter(list[str])),\n"
                        "    \"score\": (\"int, Field(ge=1, le=100) — coerce first, then the bounds\", TypeAdapter(ScoreField)),\n"
                        "    \"handle\": (\"str + @field_validator — canonical_handle normalizes\", TypeAdapter(HandleField)),\n"
                        "}"
                    ),
                ),
            ],
        ),
        # ── 7. pydantic-settings ────────────────────────────────────────────
        Section(
            id="pydantic-settings",
            title="pydantic-settings: configuration is a model too",
            blocks=[
                TextBlock(
                    id="settings-pitch",
                    kind="text",
                    text=(
                        "Environment configuration is validation at a "
                        "different boundary — bytes from the environment "
                        "meeting typed fields — and pydantic-settings "
                        "solves it with the same machinery you already know: "
                        "a BaseSettings model whose fields carry defaults, "
                        "an env_prefix so FDG_ENV maps to env without "
                        "collision, and identical coercion rules "
                        "(FDG_DEBUG=\"true\" becomes a real bool by the "
                        "pipeline from section 3). You get everything a "
                        "model gets: unknown-typed env vars rejected at "
                        "boot instead of exploding at 3am in a request, "
                        "frozen instances nobody mutates mid-process, and a "
                        "typed singleton every handler receives through "
                        "Depends(get_config). This server's whole "
                        "configuration layer is one class and one cached "
                        "accessor — quoted here in full, because it is the "
                        "entire file's worth of substance:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="settings-config",
                    language="py",
                    caption="The server's entire configuration surface.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "class AppConfig(BaseSettings):\n"
                        "    \"\"\"Process-wide settings; each field name doubles as its env var name.\"\"\"\n"
                        "\n"
                        "    model_config = SettingsConfigDict(env_prefix=\"FDG_\", frozen=True)\n"
                        "\n"
                        "    env: str = \"dev\"\n"
                        "    debug: bool = False\n"
                        "    database_url: str = \"postgresql+asyncpg://postgres:guide@localhost:5432/guide\"\n"
                        "    redis_url: str = \"redis://localhost:6379\"\n"
                        "    mongo_url: str = \"mongodb://localhost:27017\"\n"
                        "    log_level: str = \"info\"\n"
                        "\n"
                        "\n"
                        "@lru_cache(maxsize=1)\n"
                        "def get_config() -> AppConfig:\n"
                        "    \"\"\"Return the process-wide config instance (one per process).\"\"\"\n"
                        "    return AppConfig()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="settings-coda",
                    text=(
                        "Two decisions in those lines earn their keep "
                        "weekly. Defaults that boot anywhere: every knob has "
                        "a dev-safe default, so the app starts with zero "
                        "environment and compose files only OVERRIDE what "
                        "differs — an empty FDG_ environment is a valid "
                        "environment, which keeps tests and fresh clones "
                        "honest. And the cache: AppConfig() reads the "
                        "environment at construction, so the process wants "
                        "exactly one instance — lru_cache(maxsize=1) makes "
                        "get_config idempotent, tests clear the cache to "
                        "vary the environment per case, and the dependency "
                        "injection topic (06) will show dependency_overrides "
                        "swapping the whole thing for a fake. Secrets are "
                        "the deliberate non-goal here: no FDG_ variable in "
                        "this file is a secret, and the deployment topics "
                        "keep it that way — secrets arrive at runtime from "
                        "the platform, never baked into a settings class's "
                        "defaults."
                    ),
                ),
            ],
        ),
        # ── 8. pydantic-core ────────────────────────────────────────────────
        Section(
            id="pydantic-core",
            title="pydantic-core: the Rust engine (and free JSON Schema)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="core-pitch",
                    text=(
                        "Since pydantic v2, the package you import is two "
                        "projects: pydantic, the Python API — models, "
                        "decorators, docs — and pydantic-core, the "
                        "validation engine underneath, written in Rust on "
                        "pyo3 with Python-facing types generated from a Rust "
                        "schema definition. The split is not marketing: the "
                        "hot loop of validation and serialization — walk "
                        "fields, coerce, check constraints, build — runs as "
                        "compiled native code per field type, which is where "
                        "the widely-reported v1-to-v2 speedups came from, "
                        "and the Python layer is a thin, well-typed veneer "
                        "over it. You can see the seam in every traceback "
                        "you have met in this guide's tests: error types "
                        "like int_parsing and greater_than_equal are "
                        "pydantic-core's vocabulary, surfaced verbatim "
                        "through the Python API. The honest performance "
                        "claim is qualitative — the engine compiles your "
                        "schema once into native validators, so per-request "
                        "work is native-code field dispatch, not Python "
                        "reflection — and this guide will MEASURE rather "
                        "than assert when the performance topic (38) builds "
                        "its benchmark demo. What this topic can show "
                        "concretely is the engine's second gift: schemas as "
                        "data."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="core-schema",
                    text=(
                        "model_json_schema() introspects any model into a "
                        "standard JSON Schema document — property names, "
                        "types, required lists, and the constraints you "
                        "declared with Field, translated (ge/le become "
                        "minimum/maximum; Literal becomes enum). This is the "
                        "same generation path that gives FastAPI its "
                        "OpenAPI for free: response models become schema "
                        "components, and the docs you browse at /docs are "
                        "renderings of documents nobody hand-wrote. The "
                        "lab's schema endpoint is three lines of real code "
                        "— wrap the introspection in a typed payload — and "
                        "its output is a live, checkable artifact: the "
                        "specimen's score really does arrive with minimum 1 "
                        "and maximum 100, because both come from the same "
                        "ScoreField declaration the validator enforces. "
                        "Schema and enforcement cannot drift apart:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="core-schema-quote",
                    language="py",
                    caption="Schema generation, for real: introspection, not authorship.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "def build_schema_payload() -> PydLabSchemaPayload:\n"
                        "    \"\"\"The specimen's generated JSON Schema — introspection, not hand-writing.\"\"\"\n"
                        "    return PydLabSchemaPayload(\n"
                        "        model=LabSpecimen.__name__,\n"
                        "        json_schema=LabSpecimen.model_json_schema(),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="core-coda",
                    text=(
                        "One typing note for the schema endpoint's payload: "
                        "the schema document is open-shaped JSON, and this "
                        "repo types it dict[str, JsonValue] — pydantic's "
                        "recursive JSON-value type — rather than dict[str, "
                        "Any], so the payload model itself validates that "
                        "what rides the wire is pure JSON (no stray Python "
                        "objects smuggled through an Any). Small habit, "
                        "same philosophy as the whole topic: the boundary "
                        "is typed all the way down. With engine, pipeline, "
                        "validators, serialization, and schema covered, "
                        "what remains is to watch it all work at once — the "
                        "lab."
                    ),
                ),
            ],
        ),
        # ── 9. The validation lab (inline demo) ─────────────────────────────
        Section(
            id="the-validation-lab",
            title="The validation lab",
            lead="This section carries the topic's demo — drive the pipeline yourself.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="lab-pitch",
                    text=(
                        "The demo is an interactive validation laboratory. "
                        "One model under test — the strict LabSpecimen with "
                        "its constrained score, canonicalizing validator, "
                        "and cross-field rule — and two endpoints: GET "
                        "lab/schema serves the model's generated JSON "
                        "Schema, and POST lab/validate accepts a "
                        "deliberately coercion-rich body and answers with a "
                        "per-field report: what each field carried (type + "
                        "repr, exactly as JSON delivered it), what the "
                        "strict target did with it — clean, coerced (with "
                        "the value and both types), or rejected (with "
                        "pydantic's own error type and message) — and "
                        "finally whether the whole specimen validates. The "
                        "request model is permissive on purpose: its scalar "
                        "fields are unions that keep your raw spellings "
                        "(a smart union prefers the exact type — \"42\" "
                        "stays a string), so the report can show coercion "
                        "DECIDING rather than pretending. The pair of "
                        "endpoints, thin as the house style demands:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="lab-router",
                    language="py",
                    caption="The lab endpoints: schema by introspection, validation by report.",
                    source="server/guide/presentation/routers/demo/pyd.py",
                    snippet=(
                        "@router.get(\"/lab/schema\", response_model=PydLabSchemaPayload)\n"
                        "def read_lab_schema() -> PydLabSchemaPayload:\n"
                        "    \"\"\"Serve the specimen model's generated JSON Schema.\"\"\"\n"
                        "    return build_schema_payload()\n"
                        "\n"
                        "\n"
                        "@router.post(\"/lab/validate\", response_model=PydLabReportPayload, response_model_exclude_none=True)\n"
                        "def validate_lab_submission(body: LabRequest) -> PydLabReportPayload:\n"
                        "    \"\"\"Report, per field, what pydantic's lax pipeline does with the body.\"\"\"\n"
                        "    return build_validation_report(body)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="lab-request",
                    language="py",
                    caption="The permissive body: unions that keep what JSON carried.",
                    source="server/guide/domain/demos/pyd_lab.py",
                    snippet=(
                        "class LabRequest(CamelModel):\n"
                        "    \"\"\"Permissive POST body: each scalar keeps EXACTLY what JSON carried.\n"
                        "    # …\n"
                        "    \"\"\"\n"
                        "\n"
                        "    count: CountValue\n"
                        "    flag: FlagValue\n"
                        "    tags: list[str]\n"
                        "    score: ScoreValue\n"
                        "    handle: str"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="pyd:lab",
                    title="The validation laboratory",
                    description=(
                        "Edit the JSON payload and fire it at POST "
                        "/api/demo/pyd/lab/validate: each field reports what "
                        "the wire carried, what lax coercion made of it "
                        "(clean / coerced / rejected, with pydantic's own "
                        "error types), and whether the whole specimen — "
                        "constrained score, canonicalizing validator, "
                        "cross-field rule — validates. Bodies that cannot "
                        "even parse into the request model get FastAPI's own "
                        "422 envelope, rendered here as the lesson it is. "
                        "The specimen's generated JSON Schema rides alongside."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="lab-coda",
                    text=(
                        "Three experiments to run in the lab, one per lesson."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="lab-experiments-list",
                    ordered=False,
                    items=[
                        "Coercion — send count \"42\", flag \"true\", score "
                        "\"100\", handle with spaces and capitals: every row "
                        "reads coerced, and the specimen dump shows the typed, "
                        "normalized end state.",
                        "Constraint — drop score to 0: the row is rejected with "
                        "greater_than_equal, the exact type string from section "
                        "3's pipeline, and the specimen fails without any field "
                        "being wrong-shaped.",
                        "Boundary — make tags a plain string: the request model "
                        "itself refuses, FastAPI's 422 envelope answers before "
                        "the lab runs, and the client renders it through the "
                        "family error panel with the request id — the boundary "
                        "doing its job, visibly.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="lab-hidden-fourth",
                    text=(
                        "And one hidden fourth: set flag true "
                        "with tags empty — every field green, specimen "
                        "red; the @model_validator, deciding."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Pydantic's boundary, probed from the shell.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour "
                        "drives the whole topic against the live app: the "
                        "page you read (models serving models), the lab's "
                        "generated schema, a coercion-rich POST, a "
                        "constraint rejection, and the 422 envelope a "
                        "refused body earns. Plain curl; python3 -m "
                        "json.tool is the only helper:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this page itself — a Topic model, serialized by the models it teaches\n"
                        "curl -s localhost:8000/api/content/pydantic | python3 -m json.tool | head -n 14"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-schema",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the lab's schema — generated from LabSpecimen; note score's minimum/maximum\n"
                        "curl -s localhost:8000/api/demo/pyd/lab/schema | python3 -m json.tool | head -n 20"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-validate",
                    language="bash",
                    source=None,
                    snippet=(
                        "# a coercion-rich body: strings for numbers, \"true\" for bool, a messy handle\n"
                        "curl -s -X POST localhost:8000/api/demo/pyd/lab/validate \\\n"
                        "  -H 'content-type: application/json' \\\n"
                        "  -d '{\"count\":\"42\",\"flag\":\"true\",\"tags\":[\"boundary\",\"types\"],\"score\":\"100\",\"handle\":\"  Grace Hopper \"}' \\\n"
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-constraint",
                    language="bash",
                    source=None,
                    snippet=(
                        "# constraint rejection: score out of bounds — the row names the error type\n"
                        "curl -s -X POST localhost:8000/api/demo/pyd/lab/validate \\\n"
                        "  -H 'content-type: application/json' \\\n"
                        "  -d '{\"count\":7,\"flag\":true,\"tags\":[\"x\"],\"score\":0,\"handle\":\"ok\"}' \\\n"
                        "  | python3 -m json.tool | grep -B 2 -A 6 '\"score\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-422",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the refusal: tags must be a list — FastAPI's own 422, normalized details\n"
                        "curl -s -X POST localhost:8000/api/demo/pyd/lab/validate \\\n"
                        "  -H 'content-type: application/json' \\\n"
                        "  -d '{\"count\":7,\"flag\":true,\"tags\":\"oops\",\"score\":5,\"handle\":\"ok\"}' \\\n"
                        "  | python3 -m json.tool"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Every stop on the tour was a claim made earlier in "
                        "this topic, now with a request id attached: the "
                        "content route is the Topic model from section 1 "
                        "answering for itself; the schema endpoint is "
                        "introspection, minimum and maximum arriving from "
                        "the same Field that enforces them; the coercion "
                        "POST shows lax mode deciding, field by field, with "
                        "the specimen's normalized end state closing the "
                        "loop; and the 422 is the normalized {loc, msg, "
                        "type} envelope from section 3's handler, on the "
                        "exact kind of body it exists for. The next topic "
                        "climbs one layer up the same wall: FastAPI's "
                        "dependency injection — how these typed models and "
                        "every other dependency arrive at your handlers "
                        "without either side knowing how."
                    ),
                ),
            ],
        ),
    ],
)
