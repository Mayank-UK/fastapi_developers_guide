"""The perf-bench endpoint (topic 38, area ``perf``).

Pins the wire contract (GET /api/demo/perf/bench): four compression rows
(two REAL payloads × two gzip levels), the hygiene pair (threadpool vs
on-loop) with live probes, the introspected loop/protocol/pool/GC rows,
and the health receipt after the whole bench. Timing asserts are
deliberately RELATIVE or generously floored (topic 35's precedent: shared
CI hardware is noisy; the starvation contrast is physics — a blocked
loop cannot fire timers). The self-limiting contract is pinned too: the
whole bench stays bounded and an immediate /api/health after it still
answers promptly — the demo never wedges the shared loop.
"""

from typing import Any

from fastapi.testclient import TestClient

BENCH_PATH = "/api/demo/perf/bench"

LOOP_ROW_IDS = ["loop-class", "uvloop-selected", "http-protocol", "versions"]
POOL_ROW_IDS = [
    "dialect-driver",
    "pool-class",
    "checkedout-now",
    "pool-timeout",
    "pool-status",
]
GC_ROW_IDS = ["gc-enabled", "gc-thresholds", "gc-counts", "gc-collections", "gc-frozen"]


def rows_by_id(body: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    """The fact rows of one block, flat-mapped by id."""
    return {row["id"]: row for row in body[key]}


def test_serves_four_compression_rows_over_the_two_real_payloads(client: TestClient) -> None:
    response = client.get(BENCH_PATH)
    assert response.status_code == 200
    body = response.json()
    rows = body["compression"]
    assert [(r["payloadId"], r["level"]) for r in rows] == [
        ("content-index", 1),
        ("content-index", 6),
        ("performance-detail", 1),
        ("performance-detail", 6),
    ]
    for row in rows:
        assert row["rawBytes"] > 0
        assert row["gzippedBytes"] < row["rawBytes"], "real JSON text must gzip smaller"
        assert row["savedPercent"] >= 40.0, f"JSON gzip saves >40% (got {row['savedPercent']})"
        assert row["encodeMs"] >= 0.0 and row["decodeMs"] >= 0.0
        assert row["iterations"] >= 3, "the timing loops are bounded multi-iteration means"
    by_payload = {r["payloadId"]: r for r in rows if r["level"] == 1}
    assert "topics," in by_payload["content-index"]["payload"], (
        "the index row names its real payload (topic and group counts)"
    )
    assert "this very page" in by_payload["performance-detail"]["payload"]
    assert by_payload["performance-detail"]["rawBytes"] >= 30_000, "this page is a big payload"
    assert by_payload["content-index"]["rawBytes"] >= 10_000


def test_the_hygiene_pair_contrasts_contained_vs_starving(client: TestClient) -> None:
    body = client.get(BENCH_PATH).json()
    rows = {row["label"]: row for row in body["hygiene"]}
    assert [row["label"] for row in body["hygiene"]] == [
        "threadpool-offload",
        "on-loop-block",
    ]
    on_loop, threadpool = rows["on-loop-block"], rows["threadpool-offload"]
    for row in (on_loop, threadpool):
        assert row["elapsedMs"] >= 70.0, "the 80ms CPU budget must actually elapse"
        assert row["elapsedMs"] < 400.0, "each block is bounded"
        assert row["concurrentHealthStatus"] == 200, "the concurrent probe hit the real route"
    # Physics, not luck: a blocked loop cannot fire timers or serve requests.
    assert on_loop["loopLagMaxMs"] > threadpool["loopLagMaxMs"]
    assert on_loop["loopLagMaxMs"] >= 40.0
    assert on_loop["concurrentHealthMs"] > threadpool["concurrentHealthMs"]


def test_the_loop_rows_report_the_process_truth_honestly(client: TestClient) -> None:
    body = client.get(BENCH_PATH).json()
    rows = rows_by_id(body, "loop")
    assert list(rows) == LOOP_ROW_IDS
    assert rows["loop-class"]["value"].startswith(("asyncio.", "uvloop."))
    honest_prefixes = ("yes —", "no —", "httptools —", "h11 —", "not observable")
    for row_id in ("uvloop-selected", "http-protocol"):
        assert rows[row_id]["value"].startswith(honest_prefixes)
    assert "uvicorn" in rows["versions"]["value"]


def test_the_pool_rows_snapshot_the_real_engine_pool(client: TestClient) -> None:
    body = client.get(BENCH_PATH).json()
    rows = rows_by_id(body, "pool")
    assert rows["dialect-driver"]["value"] == (
        "postgresql over asyncpg (the config's database URL)"
    )
    assert rows["pool-class"]["value"].startswith("AsyncAdaptedQueuePool")
    assert rows["pool-class"]["value"].endswith("SQLAlchemy's default pool for async engines")
    assert rows["pool-timeout"]["value"].startswith("30.0s")
    assert "Pool size: 5" in rows["pool-status"]["value"]
    assert "Checked out connections" in rows["pool-status"]["value"]


def test_the_gc_rows_read_the_stdlib_collector(client: TestClient) -> None:
    body = client.get(BENCH_PATH).json()
    rows = rows_by_id(body, "gcFacts")
    assert list(rows) == GC_ROW_IDS
    assert rows["gc-enabled"]["value"] == "True"
    assert rows["gc-thresholds"]["value"].startswith("(2000, 10, 10)")
    assert rows["gc-frozen"]["value"].startswith("0")
    collection = body["gcCollection"]
    assert collection["offLoop"] is True
    assert collection["collected"] >= 0
    assert collection["elapsedMs"] >= 0.0


def test_the_demo_is_self_limiting_and_leaves_the_loop_responsive(client: TestClient) -> None:
    response = client.get(BENCH_PATH)
    body = response.json()
    receipt = body["healthAfter"]
    assert receipt["status"] == 200, "the receipt is a real /api/health after the bench"
    assert receipt["elapsedMs"] < 1000.0
    assert "measured on this very request" in body["honestyNote"]
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.elapsed.total_seconds() < 1.0, "the loop must answer immediately after the demo"
    assert response.elapsed.total_seconds() < 10.0, "the whole bench stays bounded"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][BENCH_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("PerfBenchPanel")
