import type { Result } from '../../core/result';
import type { ArchEventStorePanel } from './arch-eventstore';

/**
 * ArchEventStoreRepository — the domain-facing port for the advanced-
 * architecture topic's event-store panel. Demo components depend on
 * this interface only; the HTTP adapter lives in data/demo and is
 * wired at the composition root.
 *
 * The panel is one deterministic 2xx read: the server appended,
 * folded, rebuilt, and conflicted against a REAL EventStore port on
 * the very request that serves it — the fold steps and the rebuild
 * equality were computed, not narrated.
 */
export interface ArchEventStoreRepository {
  /** The event-store panel: history, fold, rebuild, conflict, kinship. */
  eventstore(): Promise<Result<ArchEventStorePanel>>;
}
