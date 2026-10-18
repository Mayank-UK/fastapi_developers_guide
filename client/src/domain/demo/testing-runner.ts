/**
 * Domain models for the testing topic's runner (demo block id
 * `testing:runner`) — the client-side shape of GET /api/demo/testing and
 * POST /api/demo/testing/run/{sliceId}. Field names match the server's
 * camelCase wire contract 1:1 (the DTO is the seam where wire and domain
 * may diverge later).
 *
 * The roster is four curated slices of the SERVER repo's own test files;
 * the run result is genuinely measured — every count, duration, and
 * per-test line was parsed from a real subprocess pytest round. The
 * client's own vitest suite rides as a recipe row: the server cannot
 * run it, so the panel shows the real command instead of a fake result.
 */

export interface TestingSlice {
  /** The roster id the run endpoint accepts (e.g. "unit-pure"). */
  sliceId: string;
  /** Short display title. */
  title: string;
  /** What this slice teaches, server-authored. */
  focus: string;
  /** Repo-root-relative display paths of the real test files. */
  paths: string[];
  /** What to watch for when the slice runs. */
  note: string;
}

export interface ClientRecipe {
  /** Display title — explicitly a recipe, not a run. */
  title: string;
  /** The real command that runs the client's vitest suite. */
  command: string;
  /** Why the panel shows it instead of firing it. */
  note: string;
}

export interface RunnerFacts {
  /** How the runner builds its argv, stated plainly. */
  commandTemplate: string;
  /** Where the subprocess runs (the server root). */
  cwd: string;
  /** The hard subprocess timeout, seconds. */
  timeoutSeconds: number;
  /** How the run stays off the event loop (asyncio.to_thread). */
  offLoop: string;
  /** The env marker a runner-started pytest carries (recursion guard). */
  guardEnv: string;
}

export interface TestingRunnerData {
  /** The frozen roster: four curated slices, roster order. */
  slices: TestingSlice[];
  /** The client suite's honest recipe row. */
  clientRecipe: ClientRecipe;
  /** The mechanics behind every run. */
  facts: RunnerFacts;
  /** One paragraph on the panel's honesty rules, server-authored. */
  reasoning: string;
}

export type SliceOutcome =
  | 'passed'
  | 'failed'
  | 'no_tests_ran'
  | 'timeout'
  | 'internal_error';

export type LineOutcome = 'passed' | 'failed' | 'error' | 'skipped' | 'xfail' | 'xpass';

export interface SliceTestLine {
  /** The pytest nodeid (e.g. "tests/domain/test_x.py::test_y"). */
  nodeid: string;
  /** That test's verdict as pytest printed it. */
  outcome: LineOutcome;
}

export interface SliceRunResult {
  /** Which roster slice ran. */
  sliceId: string;
  /** The run's verdict (pytest's exit code mapped honestly). */
  outcome: SliceOutcome;
  passed: number;
  failed: number;
  skipped: number;
  errors: number;
  /** Wall-clock duration of the whole subprocess round. */
  durationMs: number;
  /** Pytest's own reported seconds; absent when the summary did not parse. */
  pytestSeconds?: number;
  /** The raw final line pytest printed — honest on the wire. */
  summaryLine: string;
  /** The exact argv the runner executed. */
  commandLine: string;
  /** Per-test lines, parsed where cheap. */
  testLines: SliceTestLine[];
  /** The slice's own note (what to watch for). */
  note: string;
}
