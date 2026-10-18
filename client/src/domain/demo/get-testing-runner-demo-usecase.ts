import type { Result } from '../../core/result';
import type { SliceRunResult, TestingRunnerData } from './testing-runner';
import type { TestingRunnerRepository } from './testing-runner-repository';

/**
 * GetTestingRunnerDemoUseCase — the testing topic's runner (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * `execute` reads the roster; `run` fires one curated slice — each run
 * is a fresh real subprocess round with fresh counts and durations.
 */
export class GetTestingRunnerDemoUseCase {
  private readonly repository: TestingRunnerRepository;

  constructor(repository: TestingRunnerRepository) {
    this.repository = repository;
  }

  execute(): Promise<Result<TestingRunnerData>> {
    return this.repository.roster();
  }

  run(sliceId: string): Promise<Result<SliceRunResult>> {
    return this.repository.run(sliceId);
  }
}
