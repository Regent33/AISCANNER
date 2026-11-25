import type { Result } from '@shared/kernel/types/result'
import type { Settings } from '../entities/settings'

export interface ISettingsRepository {
  get(): Promise<Result<Settings>>
  save(s: Settings): Promise<Result<Settings>>
}
