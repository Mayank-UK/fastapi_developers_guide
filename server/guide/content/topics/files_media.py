"""Topic 26 — Files and media (the media-realtime group opens).

Everything so far spoke JSON; this topic moves BYTES. It opens with the
fact every file feature stands on — a request body is a STREAM, not a
variable — and builds outward from it: UploadFile and the spooling
underneath (with the workbench demo INLINE as the live lesson), downloads
with honest Content-Disposition and RFC 6266/5987 names, RFC 9110 range
requests served as 206 windows, streaming responses and the backpressure
a slow client exerts (measured live), Pillow image work on upload, and
the path-traversal family against the naming defense this repo actually
runs. One demo INLINE: files:workbench, in the UploadFile section — the
workbench's upload panel IS the lesson, and every later section's
endpoint lives on the same panel.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="files-media",
    title="Files and media",
    subtitle=(
        "Uploads as streams, UploadFile and spooling, downloads with honest "
        "Content-Disposition, RFC 9110 range requests, streaming responses and "
        "backpressure, Pillow image work, and the path-traversal family — one "
        "live workbench that uploads, serves, slices, transforms, and defends."
    ),
    group="media-realtime",
    order=26,
    sections=[
        # ── 1. Uploads are streams ─────────────────────────────────────────
        Section(
            id="uploads-are-streams",
            title="Uploads are streams",
            blocks=[
                TextBlock(
                    kind="text",
                    id="streams-pitch",
                    text=(
                        "Every request body this guide has handled so far arrived "
                        "small and JSON-shaped, so it was tempting to think of it "
                        "as a variable — the handler asks, the body is there. A "
                        "2-gigabyte video upload breaks that picture on contact: "
                        "the body arrives over minutes, in TCP-sized pieces, and "
                        "the only question is WHERE those pieces accumulate while "
                        "they arrive. An upload endpoint is not a function that "
                        "receives bytes; it is a loop that decides, chunk by "
                        "chunk, how much to hold, how much to check, and when to "
                        "say stop. Every memory blowup story in this territory — "
                        "the OOM killed by a 4 GB body, the 40 uploads that "
                        "together ate the RAM — is the same story: someone "
                        "treated a stream as a variable."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="streams-spooling-pitch",
                    text=(
                        "Starlette, and therefore FastAPI, already made the "
                        "stream-shaped decision for you on the upload path: an "
                        "uploaded part lands in a ``SpooledTemporaryFile`` — a "
                        "file-like object that lives IN RAM while it stays under "
                        "a 1 MiB threshold and silently rolls over to a real "
                        "temp file on disk the moment it crosses it. That "
                        "threshold is the memory-vs-disk trade made concrete: "
                        "small uploads (an avatar, a CSV, a config blob) pay "
                        "RAM-speed prices, and a large one stops being your "
                        "memory problem the moment it spills. The workbench "
                        "serves the number on its panel — it is the same "
                        "constant the platform uses — and the cap beside it is "
                        "the policy this guide adds on top:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="streams-thresholds",
                    ordered=False,
                    items=[
                        "RAM spool (≤1 MiB) — the body lives in memory inside the "
                        "SpooledTemporaryFile; reads are pointer math, latency is "
                        "zero, and the cost is bounded by design.",
                        "Disk rollover (>1 MiB) — the same file-like handle, "
                        "backed by a temp file; the upload costs disk, not RAM, "
                        "and the API you read it through never changes.",
                        "Hard cap (2 MiB here) — the DEMO's policy limit: the "
                        "workbench refuses bodies past 2 MiB while READING them, "
                        "before the bytes are ever fully held (production caps "
                        "sit at whatever the feature's real budget is, and the "
                        "proxy usually carries a bigger one).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="streams-cap-while-reading",
                    text=(
                        "The placement of the cap is the whole engineering: a "
                        "limit checked AFTER the body is fully read has already "
                        "lost, because the reading is the damage. The service "
                        "this topic builds reads the upload in 64 KiB chunks and "
                        "checks the running total after every extend — one chunk "
                        "over the cap is proof the body is too big, obtained "
                        "while holding at most cap-plus-one-chunk, and the "
                        "rejection is the one-taxonomy 422 envelope (the "
                        "deliberate divergence from HTTP's 413, on record in the "
                        "range section):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="streams-read-loop-quote",
                    language="py",
                    caption="The cap enforced where it must be: while the stream is being read, never after.",
                    source="server/guide/domain/files/service.py",
                    snippet=(
                        "        body = bytearray()\n"
                        "        while True:\n"
                        "            chunk = await read(READ_CHUNK_BYTES)\n"
                        "            if not chunk:\n"
                        "                break\n"
                        "            body.extend(chunk)\n"
                        "            if len(body) > MAX_UPLOAD_BYTES:\n"
                        "                # Proof of oversize, obtained without the rest of the body.\n"
                        "                validate_size(bytes(body))\n"
                        "        return self._store_upload(display_name, declared_type, bytes(body))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="streams-coda",
                    text=(
                        "Read the loop once more with the streaming hat on: "
                        "``read`` is an async callable — Starlette's own "
                        "``UploadFile.read`` — and each await is the server "
                        "yielding to the event loop while more bytes are still "
                        "in flight. Nothing about the interface promises the "
                        "body is finished, or even bounded, until the empty "
                        "chunk says so. That is why the functions that follow "
                        "all take a reader rather than a bytes value: the "
                        "signature itself is the stream lesson, and the demo "
                        "router can hand ``file.read`` straight through without "
                        "the router ever knowing how the platform spooled it."
                    ),
                ),
            ],
        ),
        # ── 2. UploadFile ──────────────────────────────────────────────────
        Section(
            id="uploadfile",
            title="UploadFile in FastAPI",
            lead="This section carries the topic's demo — the files workbench.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="uploadfile-anatomy",
                    text=(
                        "FastAPI's surface for a multipart file part is the "
                        "``UploadFile``: declare ``file: UploadFile = File(...)`` "
                        "and the framework hands you a spooled, file-like handle "
                        "with three honest attributes — ``filename`` (the "
                        "client-supplied name, a CLAIM, not a fact), "
                        "``content_type`` (the client-supplied MIME type, same "
                        "status), and async ``read``/``write``/``seek`` over the "
                        "spooled bytes, with ``.file`` exposing the underlying "
                        "file object when you need a real one. Two dependencies "
                        "make this work invisibly: python-multipart parses the "
                        "multipart body (the router imports nothing for it), and "
                        "the spooling from section one decides where the bytes "
                        "sit. The workbench router is the whole pattern — parse "
                        "the honest parts out of the handle, hand the reader to "
                        "the service, shape the outcome:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="uploadfile-router-quote",
                    language="py",
                    caption="The thin upload router: unwrap the part's claims, delegate the stream, map the outcome.",
                    source="server/guide/presentation/routers/demo/files.py",
                    snippet=(
                        "    if not file.filename:\n"
                        "        raise AppError(\n"
                        "            FailureKind.VALIDATION_FAILED,\n"
                        "            \"upload rejected — the multipart part carries no filename\",\n"
                        "        )\n"
                        "    return file.filename, file.content_type or GENERIC_CONTENT_TYPE\n"
                        "# …\n"
                        "async def upload_file(service: ServiceDep, file: Annotated[UploadFile, File()]) -> UploadOutcomeRow:\n"
                        "    \"\"\"Accept one multipart upload: streamed cap check, sniff, minted id.\"\"\"\n"
                        "    display_name, declared_type = _named_upload(file)\n"
                        "    outcome = await service.upload(display_name, declared_type, file.read)\n"
                        "    return build_upload_outcome_row(outcome)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="uploadfile-sniff-pitch",
                    text=(
                        "The part where most upload endpoints fail review is "
                        "trusting the two claims. The name is attacker-chosen "
                        "text; the content type is a string the sending side "
                        "made up — a script can declare ``image/jpeg`` over "
                        "anything. The workbench checks the CLAIM against the "
                        "body's leading MAGIC BYTES (PNG and JPEG signatures, "
                        "PDF, ZIP, GIF — plus a pragmatic text probe: no NUL "
                        "byte and clean UTF-8 reads as text) and refuses the "
                        "upload when they disagree, mapping the mismatch onto "
                        "the same 422 envelope. One honest escape hatch exists: "
                        "``application/octet-stream`` declares nothing, so it "
                        "always agrees, with the sniff recorded for the panel "
                        "to show:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="uploadfile-sniff-quote",
                    language="py",
                    caption="The sniff: what the first bytes say the body is — the declared type must agree.",
                    source="server/guide/domain/files/validation.py",
                    snippet=(
                        "    for signature, content_type in MAGIC_SIGNATURES:\n"
                        "        if body.startswith(signature):\n"
                        "            return content_type\n"
                        "    if b\"\\x00\" not in body[:512]:\n"
                        "        try:\n"
                        "            body[:512].decode(\"utf-8\")\n"
                        "        except UnicodeDecodeError:\n"
                        "            return GENERIC_CONTENT_TYPE\n"
                        "        return TEXT_CONTENT_TYPE\n"
                        "    return GENERIC_CONTENT_TYPE"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="uploadfile-demo-pitch",
                    text=(
                        "Try it: the workbench panel is this whole topic wired "
                        "live — upload the sample text file or a real one from "
                        "disk and watch the stored row come back with BOTH "
                        "names (your original, kept as data, and what the "
                        "allow-list sanitizer made of it), the sniff verdict "
                        "beside the claim, and a server-minted id that never "
                        "derived from your name at all. Push it past 2 MiB and "
                        "the 422 arrives from the read loop; declare a PNG as "
                        "JPEG and the sniff refuses it. The stored list feeds "
                        "the download and range sections, the image tab runs "
                        "the Pillow round, the traversal tester runs section "
                        "seven's defense, and the stream tab makes section "
                        "five's pacing visible chunk by chunk — one panel, "
                        "every endpoint of the topic."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="files:workbench",
                    title="The files workbench",
                    description=(
                        "GET /api/demo/files serves the panel (policy: 2 MiB "
                        "cap, 64 KiB read chunks, 1 MiB spool threshold, 96px "
                        "thumbnail box; stored inventory; endpoint tour; "
                        "honesty notes — the in-memory store is demo-scoped and "
                        "restart-lossy). POST /api/demo/files/upload accepts a "
                        "multipart file (sample file client-side, or a real "
                        "picker in a browser): streamed cap enforcement, "
                        "magic-byte sniff against the declared type (disagreement "
                        "→ 422 envelope), server-minted id. GET /stored inspects "
                        "what survived. GET /{id}/download?mode=inline|attachment "
                        "serves bytes with RFC 6266/5987 Content-Disposition; the "
                        "same path with a Range header (or ?bytes=0-99) answers "
                        "206 + Content-Range with the exact slice, invalid or "
                        "unsatisfiable windows the 422 envelope. POST /images "
                        "runs the Pillow round (decode → dimensions from pixels, "
                        "thumbnail + grayscale variants back as data URLs; "
                        "truncated data → 422). POST /traversal runs a submitted "
                        "name through the allow-list + containment defense and "
                        "shows the verdict. GET /stream?chunks&chunkBytes&paceMs "
                        "streams paced ndjson chunks — each arrival timed live, "
                        "throughput computed (pacing simulated and labeled)."
                    ),
                ),
            ],
        ),
        # ── 3. Downloads and Content-Disposition ───────────────────────────
        Section(
            id="downloads-and-content-disposition",
            title="Downloads and Content-Disposition",
            blocks=[
                TextBlock(
                    kind="text",
                    id="downloads-pitch",
                    text=(
                        "A download is an ordinary response whose body happens "
                        "to be bytes — but two headers decide what the CLIENT "
                        "does with it, and both are your job. ``Content-Type`` "
                        "says what the bytes are (the workbench serves the "
                        "SNIFFED type, never the client's original claim, so a "
                        "renamed file cannot smuggle a MIME the bytes do not "
                        "have). ``Content-Disposition`` says what to do with "
                        "them: ``inline`` renders in place (an image in a page, "
                        "a PDF in the viewer), ``attachment`` saves to disk "
                        "under the filename provided. The reason to set it "
                        "EXPLICITLY rather than let the browser guess from the "
                        "type is the stored-XSS shape: user-uploaded HTML "
                        "served ``inline`` on your origin executes on your "
                        "origin — the safe default is attachment for anything "
                        "not provably renderable, and the workbench makes the "
                        "toggle a query parameter so you can watch the same "
                        "bytes take both paths."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="downloads-filename-pitch",
                    text=(
                        "Filenames are the subtle half, because header "
                        "parameter syntax predates Unicode. RFC 6266 spells "
                        "the modern answer: an ASCII-safe ``filename`` "
                        "parameter for old clients, and — for any name outside "
                        "that alphabet — a ``filename*`` extended parameter "
                        "(RFC 5987) carrying the exact UTF-8 bytes "
                        "percent-encoded. Browsers prefer ``filename*`` when "
                        "present; the ASCII fallback keeps the rest of the "
                        "toolchain working. The builder this repo runs is one "
                        "pure function — name in, header value out:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="downloads-disposition-quote",
                    language="py",
                    caption="The disposition builder: ASCII fallback + RFC 5987 extended name, one line out.",
                    source="server/guide/domain/files/disposition.py",
                    snippet=(
                        "    name = clean_display_name(display_name) or \"download\"\n"
                        "    ascii_only = name.isascii()\n"
                        "    ascii_name = name if ascii_only else _ascii_residue(name)\n"
                        "    parts = [disposition_type, f\"filename={_quote_ascii(ascii_name)}\"]\n"
                        "    if not ascii_only:\n"
                        "        encoded = urllib.parse.quote(name, safe=\"\", encoding=\"utf-8\")\n"
                        "        parts.append(f\"filename*=UTF-8''{encoded}\")\n"
                        "    return \"; \".join(parts)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="downloads-injection-note",
                    text=(
                        "Note the first thing the builder does: ``clean_display_name`` "
                        "strips every control character BEFORE the name is "
                        "placed in a header. A CR or LF inside a filename "
                        "would, on naive concatenation, split the header and "
                        "forge new ones — ``filename=\\\"x\\r\\nSet-Cookie: …\\\"`` is "
                        "the classic payload, and it dies at the boundary "
                        "because the value never reaches the wire with a "
                        "newline in it. That is the same data-stays-data "
                        "discipline topic 25 preached for SQL, applied to "
                        "headers: the user's name is DATA (safe when encoded), "
                        "and the one place it is interpreted — a filesystem "
                        "path — never receives it at all, which is section "
                        "seven's job. The terminal companion proves all of it "
                        "with curl: the same stored file downloaded with "
                        "``-OJ`` lands under your original name, attachment "
                        "mode, while ``mode=inline`` answers with the inline "
                        "disposition for the browser to render."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="downloads-nosniff-note",
                    text=(
                        "One header rides every download of this app that the "
                        "download code never sets: ``X-Content-Type-Options: "
                        "nosniff``, stamped globally by topic 25's middleware, "
                        "and it exists precisely for this section. A browser "
                        "that receives a mislabeled body may sniff the bytes "
                        "and quietly execute what the Content-Type forbade "
                        "— the MIME-confusion attack; ``nosniff`` closes that "
                        "door by making the declared type FINAL, which is why "
                        "serving the SNIFFED type (the bytes' own claim) "
                        "rather than the uploader's declared one matters: it "
                        "aligns what the browser is told with what the bytes "
                        "are, and lets the middleware's guarantee do the rest. "
                        "Download responses also carry their size — a stored "
                        "body is fully in hand, so ``Content-Length`` is exact "
                        "and the client can draw a progress bar — and when a "
                        "store grows mutable files, the validators topic 21 "
                        "taught (ETag, Last-Modified) compose with this "
                        "section's ranges through ``If-Range`` to make "
                        "resumable downloads correct, not just functional."
                    ),
                ),
            ],
        ),
        # ── 4. Range requests ──────────────────────────────────────────────
        Section(
            id="range-requests",
            title="Range requests",
            blocks=[
                TextBlock(
                    kind="text",
                    id="range-pitch",
                    text=(
                        "Range requests are the HTTP feature behind every "
                        "resumable download and every video that scrubs "
                        "instantly: the client asks for PART of a "
                        "representation — ``Range: bytes=0-1023`` — and the "
                        "server answers ``206 Partial Content`` with exactly "
                        "those bytes, a ``Content-Range`` header naming the "
                        "window and the total (``bytes 0-1023/51200``), and "
                        "``Accept-Ranges: bytes`` advertising that windows are "
                        "servable at all. The resume dance is the canonical "
                        "client: fetch until the connection dies, remember how "
                        "many bytes landed, reconnect with "
                        "``Range: bytes=<that many>-``, concatenate. RFC 9110 "
                        "defines the grammar precisely, and the three legal "
                        "single-range spellings are worth knowing by name:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="range-forms",
                    ordered=False,
                    items=[
                        "Exact window — ``bytes=0-99`` asks for bytes 0 through "
                        "99 inclusive; both numbers are byte offsets, and the "
                        "end is inclusive (100 bytes, not 99).",
                        "Open-ended — ``bytes=100-`` asks for everything from "
                        "byte 100 to the end; the canonical resume form.",
                        "Suffix — ``bytes=-100`` asks for the FINAL 100 bytes "
                        "whatever the total is; a suffix longer than the file "
                        "resolves to the whole file, and ``-0`` is defined as "
                        "unsatisfiable.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="range-parser-pitch",
                    text=(
                        "The parser this repo runs is two pure steps, and the "
                        "split is the maintainable shape: SYNTAX (does the "
                        "header match one legal spelling?) then SEMANTICS "
                        "(given the file's size, which absolute window does "
                        "that mean?). The semantic step is where the RFC's "
                        "clamping lives — an end past EOF means through the "
                        "end; a suffix longer than the file means the whole "
                        "file — and where unsatisfiability is decided:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="range-resolve-quote",
                    language="py",
                    caption="Syntax to semantics: the suffix form parses, then resolution clamps against the real size.",
                    source="server/guide/domain/files/ranges.py",
                    snippet=(
                        "    if first_text == \"\":  # the suffix form: bytes=-N\n"
                        "        if not last_text.isdigit():\n"
                        "            return None\n"
                        "        suffix_length = int(last_text)\n"
                        "        if suffix_length == 0:\n"
                        "            return None  # bytes=-0 is defined unsatisfiable\n"
                        "        return ParsedRange(first=0, suffix_length=suffix_length)\n"
                        "# …\n"
                        "    if parsed.first >= size:\n"
                        "        return None\n"
                        "    end = parsed.last if parsed.last is not None else size - 1\n"
                        "    end = min(end, size - 1)\n"
                        "    return ResolvedRange(start=parsed.first, end=end, total=size)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="range-divergence-pitch",
                    text=(
                        "Invalid and unsatisfiable ranges are where this guide "
                        "departs from the letter of the RFC, deliberately and "
                        "on record. RFC-strict behavior: an unsatisfiable "
                        "window (start at or past EOF) earns ``416 Range Not "
                        "Satisfiable``, ideally with a ``Content-Range: "
                        "bytes */51200`` body so the client can resync — and a "
                        "SYNTACTICALLY invalid Range header is not an error at "
                        "all; the RFC says the server SHOULD ignore it and "
                        "serve the full 200. This repo instead maps both onto "
                        "its ONE error taxonomy: ``validation_failed`` 422 "
                        "envelopes, same shape as every other input rejection, "
                        "with the RFC's behavior named in the details so the "
                        "divergence is a decision, not an accident — the same "
                        "choice topic 25 made for the 413 the size cap would "
                        "strictly deserve. If you build an API whose clients "
                        "resume aggressively (media, large exports), weigh the "
                        "trade honestly: 416-with-total lets a well-behaved "
                        "client self-heal; a uniform envelope keeps ONE error "
                        "contract everywhere. What you must not do is the "
                        "accidental third option — crash on the header, or "
                        "serve 206 with a wrong window."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="range-multi-note",
                    text=(
                        "Two honest scope notes the workbench pins by refusing. "
                        "MULTI-RANGE (``bytes=0-1,5-6``) is legal HTTP — a "
                        "conforming server answers ``multipart/byteranges``, "
                        "one part per window; this endpoint answers the 422 "
                        "envelope naming multi-range as unsupported, which is "
                        "the correct thing for a small API to do (the clients "
                        "that need multi-range are few, and single windows "
                        "compose client-side). ``If-Range`` — ask for a range "
                        "ONLY if the representation is unchanged since an ETag "
                        "you hold, else the full 200 — is the conditional "
                        "sibling topic 21 already taught for whole responses; "
                        "wire it the same way when a store of yours grows "
                        "mutable large files."
                    ),
                ),
            ],
        ),
        # ── 5. Backpressure streaming ──────────────────────────────────────
        Section(
            id="backpressure-streaming",
            title="Backpressure streaming",
            blocks=[
                TextBlock(
                    kind="text",
                    id="backpressure-pitch",
                    text=(
                        "The response side of streaming is the async "
                        "generator: hand FastAPI a function that YIELDS byte "
                        "chunks and it wraps a ``StreamingResponse`` around "
                        "it — the server sends each chunk as it is produced "
                        "(HTTP/1.1 frames this as chunked transfer encoding; "
                        "you never build the framing yourself) and memory "
                        "stays flat no matter how long the body is. Topic 9 "
                        "introduced the mechanism; the lesson THIS topic adds "
                        "is what the generator's awaits really are. Between "
                        "your yields, the server is SENDING — and if the "
                        "client stops reading, the socket buffer fills, the "
                        "send blocks, and your generator simply does not "
                        "advance. That pause flowing backward from a slow "
                        "consumer to a fast producer is BACKPRESSURE, and it "
                        "is free: no queue, no polling, the shape of the "
                        "await chain does it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="backpressure-demo-pitch",
                    text=(
                        "The workbench's stream tab makes the cadence visible: "
                        "the server yields one newline-delimited JSON chunk at "
                        "a time with a configurable pause between chunks, and "
                        "the client times each arrival and computes throughput "
                        "— you watch bytes flow at the pace the generator sets. "
                        "Honesty first, on the panel and in the payload: the "
                        "pacing is a SIMULATED server-side sleep, standing in "
                        "for what a genuinely slow client does to this same "
                        "generator for free (a client that stops reading stops "
                        "the send, which stops the next iteration — the sleep "
                        "just makes the stall observable on a fast loopback). "
                        "The generator itself is the whole body:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="backpressure-generator-quote",
                    language="py",
                    caption="The streamed body: one planned chunk per yield, one paced await between them.",
                    source="server/guide/domain/demos/files_workbench.py",
                    snippet=(
                        "def render_stream_chunk(plan: StreamPlan, index: int) -> bytes:\n"
                        "    \"\"\"One chunk's exact bytes: a JSON line padded to the promised size.\n"
                        "# …\n"
                        "async def paced_chunks(plan: StreamPlan) -> AsyncIterator[bytes]:\n"
                        "    for index in range(1, plan.chunk_count + 1):\n"
                        "        if index > 1:\n"
                        "            await asyncio.sleep(plan.pace_ms / 1000)\n"
                        "        yield render_stream_chunk(plan, index)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="backpressure-coda",
                    text=(
                        "Three production notes the demo's shape implies. "
                        "CANCELLATION: a client that disconnects mid-stream "
                        "cancels the generator between yields — the loop above "
                        "holds no cleanup-worthy state, which is exactly why "
                        "streaming bodies should stay stateless between "
                        "chunks. BOUNDING: a generator that produces without "
                        "limit from unbounded input is the response-side "
                        "twin of the unbounded upload — cap what one response "
                        "may emit (the stream endpoint bounds chunks, bytes "
                        "per chunk, and pace by query constraints). And the "
                        "FORWARD pointer: this same mechanism with "
                        "``text/event-stream`` instead of ndjson and a "
                        "never-returning generator is server-sent events — "
                        "topic 28 builds realtime on precisely this shape, so "
                        "the pacing you can watch here is the heartbeat of "
                        "the ticker you will watch there."
                    ),
                ),
            ],
        ),
        # ── 6. Image processing ────────────────────────────────────────────
        Section(
            id="image-processing",
            title="Image processing with Pillow",
            blocks=[
                TextBlock(
                    kind="text",
                    id="images-pitch",
                    text=(
                        "Media uploads usually need DERIVED artifacts — a "
                        "thumbnail for the listing, a grayscale preview, "
                        "dimensions for layout — and that means decoding the "
                        "image for real, which is Pillow's job. The pipeline "
                        "order is the teaching: sniff first (section two — "
                        "cheap magic bytes), decode second (full validation — "
                        "the body can carry a PNG signature in front of "
                        "truncated pixel data, and only DECODING catches "
                        "that), transform third. The workbench's image round "
                        "stores the upload through the same pipeline every "
                        "upload takes, then decodes and derives two variants "
                        "— a thumbnail fitted to a 96-pixel box with the "
                        "aspect ratio kept, and a grayscale conversion — "
                        "both re-encoded as PNG so what comes back is pixels "
                        "this server produced, not bytes the uploader chose:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="images-quote",
                    language="py",
                    caption="Decode honestly, derive deterministically: truncated data dies at the boundary, not mid-transform.",
                    source="server/guide/domain/files/images.py",
                    snippet=(
                        "def _open(body: bytes) -> Image.Image:\n"
                        "    \"\"\"Decode the body fully (truncated data fails HERE, not mid-transform).\"\"\"\n"
                        "    try:\n"
                        "        image = Image.open(io.BytesIO(body))\n"
                        "        image.load()\n"
                        "    except (UnidentifiedImageError, OSError, ValueError) as error:\n"
                        "        raise AppError(\n"
                        "            FailureKind.VALIDATION_FAILED,\n"
                        "# …\n"
                        "def make_thumbnail(body: bytes, max_edge: int = THUMBNAIL_MAX_EDGE) -> bytes:\n"
                        "    \"\"\"Fit the image inside a ``max_edge`` box (aspect preserved), re-encoded PNG.\"\"\"\n"
                        "    with _open(body) as image:\n"
                        "        image.thumbnail(size=(max_edge, max_edge))\n"
                        "        buffer = io.BytesIO()\n"
                        "        image.save(buffer, format=VARIANT_FORMAT)\n"
                        "        return buffer.getvalue()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="images-dimensions-note",
                    text=(
                        "Dimensions and format come from the DECODED image, "
                        "never from the declared content type or the filename "
                        "extension — the uploaded file's row shows what the "
                        "pixels said, and the workbench displays decoded width "
                        "× height beside the sniff verdict so the two sources "
                        "of truth stay visibly separate. The re-encode as PNG "
                        "buys three things at once: determinism (identical "
                        "input yields identical output bytes, pinned by test), "
                        "size sanity (a variant is bounded by its own pixel "
                        "count, not the original's compression), and payload "
                        "hygiene — EXIF metadata, embedded thumbnails, and "
                        "any polyglot tricks in the original simply do not "
                        "survive a decode-then-re-encode of the pixels alone."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="images-loop-note",
                    text=(
                        "One async-honesty note before the demo scales it up: "
                        "Pillow decodes on the CPU, and this handler is an "
                        "``async def`` — a big image decoded inline stalls the "
                        "event loop for the decode's duration. At this demo's "
                        "2 MiB cap the stall is milliseconds; at real sizes "
                        "the honest shapes are a ``def`` endpoint (FastAPI "
                        "runs it in the threadpool) or a thread offload, and "
                        "past a second of work the right home is a background "
                        "job that derives variants asynchronously (topic 29) "
                        "while topic 38 names the never-block-the-loop rule "
                        "in full. The pattern to carry is the boundary: "
                        "hostile bytes get validated at the edge, and heavy "
                        "work gets scheduled, never smuggled into the loop."
                    ),
                ),
            ],
        ),
        # ── 7. Path traversal ──────────────────────────────────────────────
        Section(
            id="path-traversal",
            title="Path traversal",
            blocks=[
                TextBlock(
                    kind="text",
                    id="traversal-pitch",
                    text=(
                        "Path traversal is injection wearing a filename: "
                        "user input that crosses into a place where it is "
                        "INTERPRETED — here, as a filesystem path. The ``../`` "
                        "family asks the filesystem to walk OUT of the "
                        "directory you chose, and when the fragment is joined "
                        "unchecked into a storage path, ``../../etc/passwd`` "
                        "reads a file you never meant to serve — or worse, a "
                        "POST body that WRITES one. Topic 25 stated the family "
                        "cure as one sentence — data stays data — and "
                        "promised this topic implements it; here is the "
                        "implementation, and its first rule is the one that "
                        "makes every vector in the family boring:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="traversal-vectors",
                    ordered=False,
                    items=[
                        "Relative escape — ``../../etc/passwd``: separators "
                        "and dots outside the allow-list vanish, leaving the "
                        "inert residue ``etcpasswd``.",
                        "Mixed separators — ``..\\\\windows\\\\system32``: "
                        "backslash is a separator on Windows, so deny-listing "
                        "only ``/`` loses; an allow-list never meets the "
                        "question.",
                        "Absolute path — ``/etc/passwd``: the leading "
                        "separator is filtered like any other disallowed "
                        "character, and a residue cannot re-acquire one.",
                        "Unicode tricks — RTL overrides and look-alikes: "
                        "non-ASCII is dropped entirely, so the games never "
                        "arrive.",
                        "Dot-only names — ``..`` and ``...`` and ``.hidden``: "
                        "dot-stripping leaves nothing, and NOTHING is a "
                        "rejection (None), never a silent default name.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="traversal-sanitizer-quote",
                    language="py",
                    caption="The allow-list sanitizer, and the resolve-then-contain check behind it.",
                    source="server/guide/domain/files/naming.py",
                    snippet=(
                        "ALLOWED_CHARACTERS: Final[re.Pattern[str]] = re.compile(r\"[^A-Za-z0-9._-]\")\n"
                        "# …\n"
                        "def sanitize_filename(name: str) -> str | None:\n"
                        "    stripped = ALLOWED_CHARACTERS.sub(\"\", name)\n"
                        "    stripped = stripped.lstrip(\".\")\n"
                        "    trimmed = stripped[:MAX_SANITIZED_LENGTH].rstrip(\".\")\n"
                        "    if len(trimmed) < MIN_SANITIZED_LENGTH:\n"
                        "        return None\n"
                        "    return trimmed\n"
                        "# …\n"
                        "    resolved_root = Path(root).resolve()\n"
                        "    resolved = (resolved_root / user_fragment).resolve()\n"
                        "    try:\n"
                        "        resolved.relative_to(resolved_root)\n"
                        "    except ValueError:\n"
                        "        return None\n"
                        "    return str(resolved)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="traversal-defense-pitch",
                    text=(
                        "Two layers, deliberately. The ALLOW-LIST is the "
                        "primary defense: keep only ``[A-Za-z0-9._-]`` and the "
                        "attacker's entire vocabulary is those characters — "
                        "deny-lists lose to the spelling you forgot, allow-"
                        "lists cannot. The ``safe_join`` containment check is "
                        "the belt-and-braces layer for the day a fragment "
                        "genuinely must shape a path: ``resolve()`` collapses "
                        "every ``..`` and symlink spelling into the real "
                        "absolute path, and the result must sit INSIDE the "
                        "resolved root — with ``relative_to``, not a naive "
                        "``startswith`` (which would admit ``/etc/passwd`` "
                        "when your root is ``/etc/passwd-vault``). And the "
                        "workbench adds the layer that makes both almost "
                        "ceremonial: storage keys are SERVER-MINTED ids "
                        "(``f-<hex>``), so no user string ever becomes a path "
                        "fragment here at all — your name travels as data, "
                        "encoded into headers on the way out (section three) "
                        "and shown beside its sanitized residue on the panel. "
                        "The traversal tester runs any name you dare submit "
                        "through all three layers and shows every verdict."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — a real upload, a real 206, a rejected traversal.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Seven stops: a multipart upload with ``-F`` and the "
                        "metadata it returns, the stored inventory, a "
                        "download saved under the server's filename with "
                        "``-OJ``, a range request answered 206 with "
                        "Content-Range and the exact slice (plus an invalid "
                        "window's 422), the Pillow round on a generated PNG, "
                        "the traversal attempt the defense dismantles, and "
                        "the paced stream watched arriving chunk by chunk. "
                        "The stack is up; every command answers from the real "
                        "substrate this topic built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-upload",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — upload with -F: the stored row, both names, the sniff verdict\n"
                        "printf 'the guide, chapter 26 — bytes over the wire' > /tmp/chapter26.txt\n"
                        "curl -s -F 'file=@/tmp/chapter26.txt;type=text/plain' localhost:8000/api/demo/files/upload \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"id:\", b[\"file\"][\"fileId\"], \"· display:\", b[\"file\"][\"displayName\"], \\\n"
                        "\"· sanitized:\", b[\"file\"][\"sanitizedName\"], \"· sniff:\", b[\"sniff\"][\"sniffedType\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stored",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the inventory: what survived, with claim beside sniff\n"
                        "curl -s localhost:8000/api/demo/files/stored \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"count:\", b[\"count\"]); \\\n"
                        "[print(\" \", f[\"fileId\"], f[\"displayName\"], \"·\", f[\"declaredType\"], \"vs\", f[\"sniffedType\"], \"·\", f[\"sizeBytes\"], \"B\") for f in b[\"files\"]]'\n"
                        "# oversized upload → the 422 envelope, cap enforced while reading\n"
                        "head -c 3000000 /dev/zero > /tmp/too-big.bin\n"
                        "curl -s -o /dev/null -w 'oversize: %{http_code}\\n' \\\n"
                        "  -F 'file=@/tmp/too-big.bin;type=application/octet-stream' localhost:8000/api/demo/files/upload"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-download",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — download with -OJ: save under the server-provided filename\n"
                        "FID=$(curl -s localhost:8000/api/demo/files/stored \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"files\"][0][\"fileId\"])')\n"
                        "cd /tmp && curl -sOJ \"localhost:8000/api/demo/files/$FID/download\" && ls -l chapter26.txt\n"
                        "curl -sD - -o /dev/null \"localhost:8000/api/demo/files/$FID/download?mode=inline\" \\\n"
                        "  | grep -iE 'content-disposition|accept-ranges|content-type'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-range",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — one range window: 206 + Content-Range + the exact slice; then the refusals\n"
                        "curl -sD - -H 'Range: bytes=0-4' \"localhost:8000/api/demo/files/$FID/download\" \\\n"
                        "  | grep -aE 'HTTP/|content-range' ; echo\n"
                        "curl -s -H 'Range: bytes=0-4' \"localhost:8000/api/demo/files/$FID/download\"; echo\n"
                        "curl -s -o /dev/null -w 'past-EOF range: %{http_code}\\n' \\\n"
                        "  -H 'Range: bytes=99999-' \"localhost:8000/api/demo/files/$FID/download\"\n"
                        "curl -s -o /dev/null -w 'garbage range:  %{http_code}\\n' \\\n"
                        "  -H 'Range: bytes=a-b' \"localhost:8000/api/demo/files/$FID/download\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-images",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the Pillow round: dimensions from the pixels, variants derived\n"
                        "python3 -c \"from PIL import Image; Image.new('RGB', (320, 180), (30, 90, 200)).save('/tmp/sky.png')\"\n"
                        "curl -s -F 'file=@/tmp/sky.png;type=image/png' localhost:8000/api/demo/files/images \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"decoded:\", b[\"width\"], \"x\", b[\"height\"], b[\"decodedFormat\"], \\\n"
                        "\"· thumbnail:\", b[\"thumbnailBytes\"], \"B · grayscale:\", b[\"grayscaleBytes\"], \"B\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-traversal",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the traversal attempt: sanitized residue, containment verdict, minted key\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"name\": \"../../etc/passwd\"}' localhost:8000/api/demo/files/traversal \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"submitted:\", b[\"submittedName\"], \"· sanitized:\", b[\"sanitizedName\"], \\\n"
                        "\"· accepted:\", b[\"accepted\"], \"· naive join would be:\", b[\"naiveJoinTarget\"]); \\\n"
                        "print(\"key:\", b[\"storageKey\"])'\n"
                        "curl -s -o /dev/null -w 'upload of that name: %{http_code}\\n' \\\n"
                        "  -F 'file=@/tmp/chapter26.txt;filename=../../etc/passwd;type=text/plain' \\\n"
                        "  localhost:8000/api/demo/files/upload"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stream",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — the paced stream: watch chunks arrive one per interval\n"
                        "curl -sN --no-buffer 'localhost:8000/api/demo/files/stream?chunks=5&chunkBytes=128&paceMs=400' \\\n"
                        "  | while read -r line; do echo \"t=$(date +%S.%N | cut -c1-9)  $line\"; done\n"
                        "# and the panel: policy, notes, and this topic's own content map\n"
                        "curl -s localhost:8000/api/demo/files \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"cap:\", b[\"policy\"][\"maxUploadBytes\"], \"· spool at:\", b[\"policy\"][\"spoolThresholdBytes\"]); \\\n"
                        "[print(\" -\", n) for n in b[\"honestyNotes\"]]'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–3 walk one file's whole life: uploaded under "
                        "a server-minted id with its name kept as data, listed "
                        "with the sniff beside the claim, downloaded under the "
                        "original name because the header carried it encoded. "
                        "Stop 4 slices it — a 206 with the first five bytes on "
                        "the wire, and the two refusal shapes this guide "
                        "chose over 416. Stops 5–6 do the media work — pixels "
                        "decoded, variants derived, a hostile name dismantled "
                        "to its residue — and stop 7 watches backpressure's "
                        "cadence arrive in real time. That opens the media "
                        "group; from here the guide broadens outward again — "
                        "languages next (27), then the realtime pair this "
                        "topic's stream keeps pointing at (28)."
                    ),
                ),
            ],
        ),
    ],
)
