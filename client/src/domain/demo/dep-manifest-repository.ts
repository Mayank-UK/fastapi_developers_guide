import type { Result } from '../../core/result';
import type { DepsManifestPanel } from './dep-manifest';

/**
 * DepsManifestRepository — the domain-facing port for the
 * dependency-management topic's manifest panel. Demo components depend on
 * this interface only; the HTTP adapter lives in data/demo and is wired at
 * the composition root.
 *
 * The panel is one honest 2xx read of the server's real manifest and lock;
 * degradation arrives as `available: false` INSIDE a successful payload,
 * not as a failure.
 */
export interface DepsManifestRepository {
  /** The panel: groups, direct pins vs ranges, agreement, tree, counts. */
  panel(): Promise<Result<DepsManifestPanel>>;
}
