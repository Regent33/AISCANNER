import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { Settings } from '../entities/settings'
import type { ISettingsRepository } from '../repositories/settingsRepository'

export class GetSettings implements IUseCase<void, Settings> {
  private readonly repo: ISettingsRepository
  constructor(repo: ISettingsRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<Settings>> {
    return this.repo.get()
  }
}
