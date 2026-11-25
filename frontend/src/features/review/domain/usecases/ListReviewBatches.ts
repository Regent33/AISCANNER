import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { BatchOption } from '../entities/reviewItem'
import type { IReviewRepository } from '../repositories/reviewRepository'

export class ListReviewBatches implements IUseCase<TestId, BatchOption[]> {
  private readonly repo: IReviewRepository
  constructor(repo: IReviewRepository) {
    this.repo = repo
  }

  execute(testId: TestId): Promise<Result<BatchOption[]>> {
    return this.repo.listBatches(testId)
  }
}
