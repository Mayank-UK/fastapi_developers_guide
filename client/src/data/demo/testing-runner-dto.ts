import type {
  LineOutcome,
  SliceOutcome,
  SliceRunResult,
  SliceTestLine,
  TestingRunnerData,
  TestingSlice,
} from '../../domain/demo/testing-runner';
import {
  isRecord,
  optionalNumber,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * TestingRunnerDTO — the wire/transport shape of the runner panel and
 * its run results. Mirrors the domain model 1:1 (the interface is the
 * seam where wire and domain may diverge); the `fromJson` builders
 * construct ONLY the listed fields (whitelist) and throw on any shape
 * violation, which parseDto upgrades to an InvalidResponseException.
 * `pytestSeconds` is the one optional field (the server omits it when
 * the summary line did not parse); everything else is always present.
 */

export type TestingRunnerDto = TestingRunnerData;
export type SliceRunDto = SliceRunResult;

const SLICE_OUTCOMES: readonly string[] = [
  'passed',
  'failed',
  'no_tests_ran',
  'timeout',
  'internal_error',
];

const LINE_OUTCOMES: readonly string[] = [
  'passed',
  'failed',
  'error',
  'skipped',
  'xfail',
  'xpass',
];

/** Deserialize + validate the /api/demo/testing roster payload. */
export function testingRunnerDtoFromJson(body: unknown): TestingRunnerDto {
  if (!isRecord(body)) throw new Error('testing runner must be an object');
  return {
    slices: requiredArray(body, 'slices').map(sliceFromJson),
    clientRecipe: recipeFromJson(requiredRecord(body, 'clientRecipe')),
    facts: factsFromJson(requiredRecord(body, 'facts')),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate one run result from POST /api/demo/testing/run/{id}. */
export function sliceRunDtoFromJson(body: unknown): SliceRunDto {
  if (!isRecord(body)) throw new Error('slice run must be an object');
  const outcome = requiredString(body, 'outcome');
  if (!SLICE_OUTCOMES.includes(outcome)) {
    throw new Error(`unknown slice outcome "${outcome}"`);
  }
  return {
    sliceId: requiredString(body, 'sliceId'),
    outcome: outcome as SliceOutcome,
    passed: requiredNumber(body, 'passed'),
    failed: requiredNumber(body, 'failed'),
    skipped: requiredNumber(body, 'skipped'),
    errors: requiredNumber(body, 'errors'),
    durationMs: requiredNumber(body, 'durationMs'),
    pytestSeconds: optionalNumber(body, 'pytestSeconds'),
    summaryLine: requiredString(body, 'summaryLine'),
    commandLine: requiredString(body, 'commandLine'),
    testLines: requiredArray(body, 'testLines').map(testLineFromJson),
    note: requiredString(body, 'note'),
  };
}

/** Convert transport DTOs into domain models (identity while 1:1). */
export function toTestingRunner(dto: TestingRunnerDto): TestingRunnerData {
  return dto;
}

export function toSliceRun(dto: SliceRunDto): SliceRunResult {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function sliceFromJson(body: unknown): TestingSlice {
  if (!isRecord(body)) throw new Error('slice must be an object');
  return {
    sliceId: requiredString(body, 'sliceId'),
    title: requiredString(body, 'title'),
    focus: requiredString(body, 'focus'),
    paths: requiredArray(body, 'paths').map((path) => {
      if (typeof path !== 'string') throw new Error('slice path must be a string');
      return path;
    }),
    note: requiredString(body, 'note'),
  };
}

function recipeFromJson(body: Record<string, unknown>): TestingRunnerData['clientRecipe'] {
  return {
    title: requiredString(body, 'title'),
    command: requiredString(body, 'command'),
    note: requiredString(body, 'note'),
  };
}

function factsFromJson(body: Record<string, unknown>): TestingRunnerData['facts'] {
  return {
    commandTemplate: requiredString(body, 'commandTemplate'),
    cwd: requiredString(body, 'cwd'),
    timeoutSeconds: requiredNumber(body, 'timeoutSeconds'),
    offLoop: requiredString(body, 'offLoop'),
    guardEnv: requiredString(body, 'guardEnv'),
  };
}

function testLineFromJson(body: unknown): SliceTestLine {
  if (!isRecord(body)) throw new Error('test line must be an object');
  const outcome = requiredString(body, 'outcome');
  if (!LINE_OUTCOMES.includes(outcome)) {
    throw new Error(`unknown test line outcome "${outcome}"`);
  }
  return {
    nodeid: requiredString(body, 'nodeid'),
    outcome: outcome as LineOutcome,
  };
}
