import type { HttpClient } from '@shared/infrastructure/http/httpClient'
import type { NewTestDto, RegionDto, TestDto } from '../../models/testDto'

type Doc = 'key' | 'syllabus'

export class TestRemoteDataSource {
  private readonly http: HttpClient
  constructor(http: HttpClient) {
    this.http = http
  }

  list() {
    return this.http.get<TestDto[]>('/tests')
  }

  create(body: NewTestDto) {
    return this.http.post<TestDto>('/tests', body)
  }

  sendText<T>(id: number, doc: Doc, text: string) {
    return this.http.post<T>(`/tests/${id}/${doc}`, { text })
  }

  sendFile<T>(id: number, doc: Doc, file: File) {
    return this.http.upload<T>(`/tests/${id}/${doc}`, 'file', [file])
  }

  uploadSample(id: number, file: File) {
    return this.http.upload<unknown>(`/tests/${id}/sample`, 'file', [file])
  }

  printableUrl(id: number) {
    return this.http.url(`/tests/${id}/printable.pdf`)
  }

  sampleUrl(id: number) {
    return this.http.url(`/tests/${id}/sample`)
  }

  setRegions(id: number, regions: RegionDto[]) {
    return this.http.put<unknown>(`/tests/${id}/redaction`, { regions })
  }
}
