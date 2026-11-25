import type { HttpClient } from '@shared/infrastructure/http/httpClient'
import type { ReportDto } from '../../models/reportDto'

export class ReportRemoteDataSource {
  private readonly http: HttpClient
  constructor(http: HttpClient) {
    this.http = http
  }

  tests() {
    return this.http.get<{ id: number; name: string }[]>('/tests')
  }

  report(testId: number) {
    return this.http.get<ReportDto>(`/tests/${testId}/report`)
  }

  pdfUrl(testId: number) {
    return this.http.url(`/tests/${testId}/report.pdf`)
  }
}
