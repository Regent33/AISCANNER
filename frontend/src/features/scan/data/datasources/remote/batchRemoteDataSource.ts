import type { HttpClient } from '@shared/infrastructure/http/httpClient'
import type { BatchDto, ScannerDto, ScanRequestDto, TestOptionDto, UploadDto } from '../../models/batchDto'

export class BatchRemoteDataSource {
  private readonly http: HttpClient
  constructor(http: HttpClient) {
    this.http = http
  }

  tests() {
    return this.http.get<TestOptionDto[]>('/tests')
  }

  list(testId: number) {
    return this.http.get<BatchDto[]>('/batches', { test_id: testId })
  }

  create(testId: number) {
    return this.http.post<BatchDto>('/batches', { test_id: testId })
  }

  get(id: number) {
    return this.http.get<BatchDto>(`/batches/${id}`)
  }

  upload(id: number, files: File[]) {
    return this.http.upload<UploadDto>(`/batches/${id}/pages`, 'files', files)
  }

  scan(id: number, body: ScanRequestDto) {
    return this.http.post<unknown>(`/batches/${id}/scan`, body)
  }

  action(id: number, action: 'pause' | 'resume' | 'finish') {
    return this.http.post<BatchDto>(`/batches/${id}/${action}`)
  }

  scanners() {
    return this.http.get<ScannerDto[]>('/scanners')
  }

  checkPrinter(address: string) {
    return this.http.post<ScannerDto>('/scanners/check', { address })
  }

  settings() {
    return this.http.get<{ watch_folder: string | null }>('/settings')
  }
}
