import type { Result } from '../../core/result';
import type { MongoConsoleDemo } from './mongo-console';

/**
 * MongoConsoleRepository — the domain-facing port for the mongodb
 * topic's console demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. One method, one endpoint: run the console (repeatable — the
 * seed is keyed and the demo document is deleted at the end).
 */
export interface MongoConsoleRepository {
  /** Run the scripted console with the given find tag. */
  console(tag: string): Promise<Result<MongoConsoleDemo>>;
}
