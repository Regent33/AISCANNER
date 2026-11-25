import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { Settings } from '../entities/settings'
import type { ISettingsRepository } from '../repositories/settingsRepository'

export const THRESHOLD_RANGE = [0.5, 0.99] as const

export class SaveSettings implements IUseCase<Settings, Settings> {
  private readonly repo: ISettingsRepository
  constructor(repo: ISettingsRepository) {
    this.repo = repo
  }

  async execute(s: Settings): Promise<Result<Settings>> {
    const [lo, hi] = THRESHOLD_RANGE
    if (!(s.threshold >= lo && s.threshold <= hi)) return err(new Failure(`Confidence must be between ${lo * 100}% and ${hi * 100}%.`))
    return this.repo.save({ ...s, watchFolder: s.watchFolder.trim() })
  }
}
