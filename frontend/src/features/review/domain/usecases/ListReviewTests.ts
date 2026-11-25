import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestOption } from '../entities/reviewItem'
import type { IReviewRepository } from '../repositories/reviewRepository'

export class ListReviewTests implements IUseCase<void, TestOption[]> {
  private readonly repo: IReviewRepository
  constructor(repo: IReviewRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<TestOption[]>> {
    return this.repo.listTests()
  }
}
