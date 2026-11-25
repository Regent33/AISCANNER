import { map, type Result } from '@shared/kernel/types/result'
import type { ISettingsRepository } from '../../domain/repositories/settingsRepository'
import type { Settings } from '../../domain/entities/settings'
import { toSettings, toSettingsDto } from '../mappers/settingsMapper'
import type { SettingsRemoteDataSource } from '../datasources/remote/settingsRemoteDataSource'

export class SettingsRepositoryImpl implements ISettingsRepository {
  private readonly remote: SettingsRemoteDataSource
  constructor(remote: SettingsRemoteDataSource) {
    this.remote = remote
  }

  async get(): Promise<Result<Settings>> {
    return map(await this.remote.get(), toSettings)
  }

  async save(s: Settings): Promise<Result<Settings>> {
    return map(await this.remote.put(toSettingsDto(s)), toSettings)
  }
}
