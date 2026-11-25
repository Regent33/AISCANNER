import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { Batch } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

export class ListBatches implements IUseCase<TestId, Batch[]> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  execute(testId: TestId): Promise<Result<Batch[]>> {
    return this.repo.listBatches(testId)
  }
}
