import { map, type Result } from '@shared/kernel/types/result'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import type { IBatchRepository } from '../../domain/repositories/batchRepository'
import type { Batch, ScannerDevice, ScanSource, TestOption, UploadSummary } from '../../domain/entities/batch'
import { toBatch, toScanRequest, toTestOption } from '../mappers/batchMapper'
import type { BatchRemoteDataSource } from '../datasources/remote/batchRemoteDataSource'

export class BatchRepositoryImpl implements IBatchRepository {
  private readonly remote: BatchRemoteDataSource
  constructor(remote: BatchRemoteDataSource) {
    this.remote = remote
  }

  async listTests(): Promise<Result<TestOption[]>> {
    return map(await this.remote.tests(), (ds) => ds.map(toTestOption))
  }

  async listBatches(testId: TestId): Promise<Result<Batch[]>> {
    return map(await this.remote.list(testId), (ds) => ds.map(toBatch))
  }

  async create(testId: TestId): Promise<Result<Batch>> {
    return map(await this.remote.create(testId), toBatch)
  }

  async get(id: BatchId): Promise<Result<Batch>> {
    return map(await this.remote.get(id), toBatch)
  }

  async upload(id: BatchId, files: File[]): Promise<Result<UploadSummary>> {
    return this.remote.upload(id, files)
  }

  async startSource(id: BatchId, source: ScanSource): Promise<Result<void>> {
    return map(await this.remote.scan(id, toScanRequest(source)), () => undefined)
  }

  async setPaused(id: BatchId, paused: boolean): Promise<Result<Batch>> {
    return map(await this.remote.action(id, paused ? 'pause' : 'resume'), toBatch)
  }

  async finish(id: BatchId): Promise<Result<Batch>> {
    return map(await this.remote.action(id, 'finish'), toBatch)
  }

  async findScanners(): Promise<Result<ScannerDevice[]>> {
    return this.remote.scanners()
  }

  async checkPrinter(address: string): Promise<Result<ScannerDevice>> {
    return map(await this.remote.checkPrinter(address), (d) => ({ kind: d.kind, id: d.id, name: d.name }))
  }

  async defaultWatchFolder(): Promise<Result<string>> {
    return map(await this.remote.settings(), (s) => s.watch_folder ?? '')
  }
}
