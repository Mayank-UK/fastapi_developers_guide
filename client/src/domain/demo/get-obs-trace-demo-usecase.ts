import type { Result } from '../../core/result';
import type { ObsTraceRepository } from './obs-trace-repository';
import type { TraceFanout } from './obs-trace';

/**
 * GetObsTraceDemoUseCase — the observability topic's trace fan-out: one
 * live read where the server drives three REAL internal requests through
 * the running app and correlates each round's derived request id across
 * the echoed header, the error envelope, and the log rows it produced.
 */
export class GetObsTraceDemoUseCase {
  private readonly repository: ObsTraceRepository;

  constructor(repository: ObsTraceRepository) {
    this.repository = repository;
  }

  /** The fan-out: the trace root, the three real rounds, the correlation. */
  fanout(): Promise<Result<TraceFanout>> {
    return this.repository.fanout();
  }
}
