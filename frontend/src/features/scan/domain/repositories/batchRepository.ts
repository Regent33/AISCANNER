import type { Result } from '@shared/kernel/types/result'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import type { Batch, ScannerDevice, ScanSource, TestOption, UploadSummary } from '../entities/batch'

export interface IBatchRepository {
  listTests(): Promise<Result<TestOption[]>>
  listBatches(testId: TestId): Promise<Result<Batch[]>>
  create(testId: TestId): Promise<Result<Batch>>
  get(id: BatchId): Promise<Result<Batch>>
  upload(id: BatchId, files: File[]): Promise<Result<UploadSummary>>
  startSource(id: BatchId, source: ScanSource): Promise<Result<void>>
  setPaused(id: BatchId, paused: boolean): Promise<Result<Batch>>
  finish(id: BatchId): Promise<Result<Batch>>
  defaultWatchFolder(): Promise<Result<string>>
  findScanners(): Promise<Result<ScannerDevice[]>>
  checkPrinter(address: string): Promise<Result<ScannerDevice>>
}
