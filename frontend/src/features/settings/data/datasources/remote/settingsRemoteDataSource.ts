import type { HttpClient } from '@shared/infrastructure/http/httpClient'
import type { SettingsDto } from '../../models/settingsDto'

export class SettingsRemoteDataSource {
  private readonly http: HttpClient
  constructor(http: HttpClient) {
    this.http = http
  }

  get() {
    return this.http.get<SettingsDto>('/settings')
  }

  put(body: Partial<SettingsDto>) {
    return this.http.put<SettingsDto>('/settings', body)
  }
}
