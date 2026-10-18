import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { ArenaRound, ArenaRoster, ArenaVerdict } from '../../domain/demo/validation-arena';
import type { ValidationArenaRepository } from '../../domain/demo/validation-arena-repository';
import type { ValidationArenaApi } from './validation-arena-api';

/**
 * ValidationArenaRepositoryImpl — adapts the arena API to the domain port.
 * Every thrown transport error (network, non-2xx envelope — including the
 * deliberate 422 a refused round body earns — malformed payload) is
 * guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class ValidationArenaRepositoryImpl implements ValidationArenaRepository {
  private readonly api: ValidationArenaApi;

  constructor(api: ValidationArenaApi) {
    this.api = api;
  }

  roster(): Promise<Result<ArenaRoster>> {
    return safeRepositoryCall(() => this.api.roster());
  }

  run(round: ArenaRound): Promise<Result<ArenaVerdict>> {
    return safeRepositoryCall(() => this.api.run(round));
  }
}
