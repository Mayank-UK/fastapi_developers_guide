"""Demo substrate area: pure payload builders for ``/api/demo`` endpoints.

Each demo area gets one module here — a pure, typed, side-effect-free
builder that a thin router calls (routers stay thin by family invariant).
The python-language topic's runtime-types demo lives in ``runtime_types.py``;
the python-runtime topic's demos live in ``runtime_async.py`` (measured
sequential-vs-gathered timings) and ``runtime_streaming.py`` (a real async
generator served as NDJSON).
"""
