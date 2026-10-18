import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { SliceRunResult, TestingRunnerData } from '../../domain/demo/testing-runner';
import type { TestingRunnerRepository } from '../../domain/demo/testing-runner-repository';
import { toSliceRun, toTestingRunner } from './testing-runner-dto';
import type { TestingRunnerApi } from './testing-runner-api';

/**
 * TestingRunnerRepositoryImpl — adapts the runner API to the domain port.
 * Every thrown transport error (network, non-2xx envelope, malformed
 * payload) is guarded by safeRepositoryCall into a Failed Result, so the
 * demo component never needs try/catch and no rejection goes unhandled.
 */
export class TestingRunnerRepositoryImpl implements TestingRunnerRepository {
  private readonly api: TestingRunnerApi;

  constructor(api: TestingRunnerApi) {
    this.api = api;
  }

  roster(): Promise<Result<TestingRunnerData>> {
    return safeRepositoryCall(async () => toTestingRunner(await this.api.roster()));
  }

  run(sliceId: string): Promise<Result<SliceRunResult>> {
    return safeRepositoryCall(async () => toSliceRun(await this.api.run(sliceId)));
  }
}
