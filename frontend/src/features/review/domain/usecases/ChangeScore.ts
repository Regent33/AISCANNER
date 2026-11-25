import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { AnswerItem } from '../entities/reviewItem'
import type { IReviewRepository } from '../repositories/reviewRepository'

type Input = { item: AnswerItem; score: number }

export class ChangeScore implements IUseCase<Input, void> {
  private readonly repo: IReviewRepository
  constructor(repo: IReviewRepository) {
    this.repo = repo
  }

  async execute({ item, score }: Input): Promise<Result<void>> {
    if (!Number.isFinite(score) || score < 0 || score > item.maxPoints)
      return err(new Failure(`Score must be between 0 and ${item.maxPoints}.`))
    return this.repo.setScore(item.responseId, score)
  }
}
