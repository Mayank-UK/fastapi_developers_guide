import type { Result } from '../../core/result';
import type { SliceRunResult, TestingRunnerData } from './testing-runner';

/**
 * TestingRunnerRepository — the domain-facing port for the testing
 * topic's runner. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 */
export interface TestingRunnerRepository {
  /** Read the roster: curated slices, the client recipe, the mechanics. */
  roster(): Promise<Result<TestingRunnerData>>;
  /** Execute one roster slice for real — the results are genuine. */
  run(sliceId: string): Promise<Result<SliceRunResult>>;
}
