import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { DepsManifestPanel } from '../../domain/demo/dep-manifest';
import type { DepsManifestRepository } from '../../domain/demo/dep-manifest-repository';
import type { DepsManifestApi } from './dep-manifest-api';

/**
 * DepsManifestRepositoryImpl — adapts the manifest API to the domain port.
 * A Failed Result means the round itself broke (network down, unparseable
 * body); a degraded panel arrives as a SUCCESSFUL available:false payload,
 * because the server could answer — it just could not read its files.
 */
export class DepsManifestRepositoryImpl implements DepsManifestRepository {
  private readonly api: DepsManifestApi;

  constructor(api: DepsManifestApi) {
    this.api = api;
  }

  panel(): Promise<Result<DepsManifestPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
