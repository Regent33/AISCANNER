import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { BatchId } from '@shared/kernel/types/ids'
import type { ReviewQueue } from '../entities/reviewItem'
import type { IReviewRepository } from '../repositories/reviewRepository'

type Input = { batchId: BatchId; pageSize: number }

/** The next page of unresolved items, lowest confidence first. Resolved items drop out, so it is always page 1. */
export class GetReviewQueue implements IUseCase<Input, ReviewQueue> {
  private readonly repo: IReviewRepository
  constructor(repo: IReviewRepository) {
    this.repo = repo
  }

  execute({ batchId, pageSize }: Input): Promise<Result<ReviewQueue>> {
    return this.repo.queue(batchId, pageSize)
  }
}
