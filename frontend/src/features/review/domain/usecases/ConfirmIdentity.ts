import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { IdentityFix, IdentityItem } from '../entities/reviewItem'
import type { IReviewRepository } from '../repositories/reviewRepository'

type Input = { item: IdentityItem; fix: IdentityFix }

/** Teacher confirms or corrects the student ID, year and section read from page 1. */
export class ConfirmIdentity implements IUseCase<Input, void> {
  private readonly repo: IReviewRepository
  constructor(repo: IReviewRepository) {
    this.repo = repo
  }

  async execute({ item, fix }: Input): Promise<Result<void>> {
    const studentId = fix.studentId.trim()
    if (!studentId || studentId.length > 32) return err(new Failure('Type the student ID as written on the paper.'))
    if (fix.year.trim().length > 16 || fix.section.trim().length > 64) return err(new Failure('Year or section is too long.'))
    return this.repo.setIdentity(item.paperId, { studentId, year: fix.year.trim(), section: fix.section.trim() })
  }
}
