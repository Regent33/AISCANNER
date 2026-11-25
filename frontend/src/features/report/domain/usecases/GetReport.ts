import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { Report } from '../entities/report'
import type { IReportRepository } from '../repositories/reportRepository'

export class GetReport implements IUseCase<TestId, Report> {
  private readonly repo: IReportRepository
  constructor(repo: IReportRepository) {
    this.repo = repo
  }

  execute(testId: TestId): Promise<Result<Report>> {
    return this.repo.get(testId)
  }
}
