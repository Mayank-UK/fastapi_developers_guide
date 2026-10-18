import type { Result } from '../../core/result';
import type { RedisPlaygroundDemo } from './redis-playground';

/**
 * RedisPlaygroundRepository — the domain-facing port for the redis
 * topic's playground demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. One method, one endpoint: run the playground (repeatable — the
 * stage is DEL'd first and left clean, and every tag gets a fresh key
 * family).
 */
export interface RedisPlaygroundRepository {
  /** Run the scripted playground with the given tag. */
  playground(tag: string): Promise<Result<RedisPlaygroundDemo>>;
}
