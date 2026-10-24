import type { Result } from '../../core/result';
import type { ThirdPartyHubPanel } from './thirdparty-hub';

/**
 * ThirdPartyHubRepository — the domain-facing port for the third-party
 * topic's hub panel. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 *
 * The panel is one honest 2xx read: the server derives every row on the
 * request that serves it (a real tomllib parse of the manifest, file
 * checks against the server tree, containment checks where the repo
 * root is mounted), so nothing here is a fabricated number.
 */
export interface ThirdPartyHubRepository {
  /** The third-party hub: decisions, integrations, secrets, quotas. */
  hub(): Promise<Result<ThirdPartyHubPanel>>;
}
