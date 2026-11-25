import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, ok, type Result } from '@shared/kernel/types/result'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import type { Batch, UploadSummary } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

type Input = { testId: TestId; batchId: BatchId | null; files: File[] }

export class UploadPages implements IUseCase<Input, { batch: Batch; summary: UploadSummary }> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  async execute({ testId, batchId, files }: Input): Promise<Result<{ batch: Batch; summary: UploadSummary }>> {
    if (files.length === 0) return err(new Failure('Choose at least one scanned page or PDF.'))
    const batch = batchId === null ? await this.repo.create(testId) : await this.repo.get(batchId)
    if (!batch.ok) return batch
    const up = await this.repo.upload(batch.value.id, files)
    return up.ok ? ok({ batch: batch.value, summary: up.value }) : up
  }
}
