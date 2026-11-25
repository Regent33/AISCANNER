import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { AnswerItem } from '../entities/reviewItem'
import type { IReviewRepository } from '../repositories/reviewRepository'

/** Keep the AI score as the final score. */
export class AcceptAnswer implements IUseCase<AnswerItem, void> {
  private readonly repo: IReviewRepository
  constructor(repo: IReviewRepository) {
    this.repo = repo
  }

  execute(item: AnswerItem): Promise<Result<void>> {
    return this.repo.setScore(item.responseId, null)
  }
}
