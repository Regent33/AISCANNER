import { container } from '@app/di/container'
import { SettingsRemoteDataSource } from '../data/datasources/remote/settingsRemoteDataSource'
import { SettingsRepositoryImpl } from '../data/repositories/settingsRepositoryImpl'
import { GetSettings } from '../domain/usecases/GetSettings'
import { SaveSettings } from '../domain/usecases/SaveSettings'

function build() {
  const repo = new SettingsRepositoryImpl(new SettingsRemoteDataSource(container.http))
  return { getSettings: new GetSettings(repo), saveSettings: new SaveSettings(repo) }
}

let mod: ReturnType<typeof build> | null = null
export const settingsModule = () => (mod ??= build())
