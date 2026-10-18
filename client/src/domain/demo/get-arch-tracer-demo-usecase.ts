import type { Result } from '../../core/result';
import type { ArchTracerRepository } from './arch-tracer-repository';
import type { ArchTracerData } from './arch-tracer';

/**
 * GetArchTracerDemoUseCase — the architecture topic's tracer (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * Carries no parameters because the demo's subject is the running app
 * itself — each execution is one fresh introspection plus two freshly
 * driven internal requests, with fresh timings and fresh request ids.
 */
export class GetArchTracerDemoUseCase {
  private readonly repository: ArchTracerRepository;

  constructor(repository: ArchTracerRepository) {
    this.repository = repository;
  }

  execute(): Promise<Result<ArchTracerData>> {
    return this.repository.read();
  }
}
