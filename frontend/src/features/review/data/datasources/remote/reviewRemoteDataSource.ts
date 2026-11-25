import type { HttpClient } from '@shared/infrastructure/http/httpClient'
import type { NamedDto, ReviewQueueDto } from '../../models/reviewDto'

export class ReviewRemoteDataSource {
  private readonly http: HttpClient
  constructor(http: HttpClient) {
    this.http = http
  }

  tests() {
    return this.http.get<NamedDto[]>('/tests')
  }

  batches(testId: number) {
    return this.http.get<NamedDto[]>('/batches', { test_id: testId })
  }

  queue(batchId: number, pageSize: number) {
    return this.http.get<ReviewQueueDto>(`/batches/${batchId}/review`, { status: 'pending', page: 1, page_size: pageSize })
  }

  patchResponse(id: number, finalScore: number | null) {
    return this.http.patch<unknown>(`/responses/${id}`, finalScore === null ? {} : { final_score: finalScore })
  }

  patchPaper(id: number, body: { student_id: string; year: string; section: string }) {
    return this.http.patch<unknown>(`/papers/${id}`, body)
  }

  cropUrl = (id: number) => this.http.url(`/responses/${id}/crop`)
  identityUrl = (id: number) => this.http.url(`/papers/${id}/identity`)
}
