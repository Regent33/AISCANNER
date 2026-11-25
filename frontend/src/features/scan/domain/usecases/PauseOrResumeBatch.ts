import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { Batch } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

/** Toggle: a paused batch resumes, a running one pauses. */
export class PauseOrResumeBatch implements IUseCase<Batch, Batch> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  execute(batch: Batch): Promise<Result<Batch>> {
    return this.repo.setPaused(batch.id, batch.status !== 'paused')
  }
}
