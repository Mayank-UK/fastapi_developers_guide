import type { Result } from '../../core/result';
import type { RuntimeStreamingRepository } from './runtime-streaming-repository';
import type { RuntimeStreamingDemoData, StreamChunk } from './runtime-streaming';

/**
 * GetRuntimeStreamingDemoUseCase — loads the python-runtime topic's
 * streaming demo. Thin orchestration seam over the repository port; the
 * optional observer forwards each arriving chunk to the presenter while
 * the final Result carries the whole stream.
 */
export class GetRuntimeStreamingDemoUseCase {
  private readonly repository: RuntimeStreamingRepository;

  constructor(repository: RuntimeStreamingRepository) {
    this.repository = repository;
  }

  execute(onChunk?: (chunk: StreamChunk) => void): Promise<Result<RuntimeStreamingDemoData>> {
    return this.repository.get(onChunk);
  }
}
