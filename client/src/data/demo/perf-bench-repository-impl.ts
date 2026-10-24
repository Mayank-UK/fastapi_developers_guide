import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { PerfBenchPanel } from '../../domain/demo/perf-bench';
import type { PerfBenchRepository } from '../../domain/demo/perf-bench-repository';
import type { PerfBenchApi } from './perf-bench-api';

/**
 * PerfBenchRepositoryImpl — adapts the perf-bench API to the domain port.
 * A Failed Result means the panel itself broke (network down, unparseable
 * body); the bench's own measured rows arrive as DATA, not as failures.
 */
export class PerfBenchRepositoryImpl implements PerfBenchRepository {
  private readonly api: PerfBenchApi;

  constructor(api: PerfBenchApi) {
    this.api = api;
  }

  panel(): Promise<Result<PerfBenchPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
