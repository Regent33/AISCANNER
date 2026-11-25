import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestOption } from '../entities/report'
import type { IReportRepository } from '../repositories/reportRepository'

export class ListReportTests implements IUseCase<void, TestOption[]> {
  private readonly repo: IReportRepository
  constructor(repo: IReportRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<TestOption[]>> {
    return this.repo.listTests()
  }
}
