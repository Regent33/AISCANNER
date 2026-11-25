import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { BatchId } from '@shared/kernel/types/ids'
import type { Batch } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

/** Scanning is over: the last paper is closed and graded. */
export class FinishBatch implements IUseCase<BatchId, Batch> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  execute(id: BatchId): Promise<Result<Batch>> {
    return this.repo.finish(id)
  }
}
