import type { Result } from '../../core/result';
import type { ValidationArenaRepository } from './validation-arena-repository';
import type { ArenaRound, ArenaRoster, ArenaVerdict } from './validation-arena';

/**
 * GetValidationArenaDemoUseCase — drives the validation topic's arena
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. Failures resolve as Failed Results — the 422 a
 * refused round body earns is an outcome the component renders through
 * the shared error panel, because it IS the lesson.
 */
export class GetValidationArenaDemoUseCase {
  private readonly repository: ValidationArenaRepository;

  constructor(repository: ValidationArenaRepository) {
    this.repository = repository;
  }

  roster(): Promise<Result<ArenaRoster>> {
    return this.repository.roster();
  }

  run(round: ArenaRound): Promise<Result<ArenaVerdict>> {
    return this.repository.run(round);
  }
}
