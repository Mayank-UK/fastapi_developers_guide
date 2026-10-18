import type { Result } from '../../core/result';
import type { RuntimeAsyncRepository } from './runtime-async-repository';
import type { RuntimeAsyncDemoData } from './runtime-async';

/**
 * GetRuntimeAsyncDemoUseCase — loads the python-runtime topic's
 * async-timing demo payload. Thin orchestration seam over the repository
 * port (react-guide use-case style); parameterless because the demo has no
 * inputs — the server measures the runs live on every request.
 */
export class GetRuntimeAsyncDemoUseCase {
  private readonly repository: RuntimeAsyncRepository;

  constructor(repository: RuntimeAsyncRepository) {
    this.repository = repository;
  }

  execute(): Promise<Result<RuntimeAsyncDemoData>> {
    return this.repository.get();
  }
}
