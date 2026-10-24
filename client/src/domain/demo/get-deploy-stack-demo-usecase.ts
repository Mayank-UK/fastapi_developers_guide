import type { Result } from '../../core/result';
import type { DeployStackPanel } from './deploy-stack';
import type { DeployStackRepository } from './deploy-stack-repository';

/**
 * GetDeployStackDemoUseCase — the deployment topic's deploy-stack
 * inspection: one live read where the server walks its own deploy
 * surface (the compose trio, the edge, the images, the pipeline, the
 * release, parity, kubernetes) and reports the runtime facts this
 * process always has, with verdicts and evidence computed at request
 * time.
 */
export class GetDeployStackDemoUseCase {
  private readonly repository: DeployStackRepository;

  constructor(repository: DeployStackRepository) {
    this.repository = repository;
  }

  /** The inspection: runtime facts, per-area verdicts, honest manuals. */
  panel(): Promise<Result<DeployStackPanel>> {
    return this.repository.panel();
  }
}
