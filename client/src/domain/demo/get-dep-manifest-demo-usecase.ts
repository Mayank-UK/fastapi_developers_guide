import type { Result } from '../../core/result';
import type { DepsManifestRepository } from './dep-manifest-repository';
import type { DepsManifestPanel } from './dep-manifest';

/**
 * GetDepsManifestDemoUseCase — the dependency-management topic's panel:
 * one live read of the server's REAL pyproject.toml + uv.lock (groups,
 * every direct range beside its locked pin, manifest/lock agreement, the
 * fastapi-rooted tree slice, whole-lock counts).
 */
export class GetDepsManifestDemoUseCase {
  private readonly repository: DepsManifestRepository;

  constructor(repository: DepsManifestRepository) {
    this.repository = repository;
  }

  /** The panel: groups, direct pins vs ranges, agreement, tree, counts. */
  panel(): Promise<Result<DepsManifestPanel>> {
    return this.repository.panel();
  }
}
