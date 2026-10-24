import type { Result } from '../../core/result';
import type { DeployStackPanel } from './deploy-stack';

/**
 * DeployStackRepository — the domain-facing port for the deployment
 * topic's deploy-stack inspection. Demo components depend on this
 * interface only; the HTTP adapter lives in data/demo and is wired at
 * the composition root.
 *
 * The panel is one honest 2xx read: the server inspects its own deploy
 * surface and runtime facts when the request arrives — verdicts computed
 * at request time, never a faked pass.
 */
export interface DeployStackRepository {
  /** The inspection: runtime facts, per-area verdicts, honest manuals. */
  panel(): Promise<Result<DeployStackPanel>>;
}
