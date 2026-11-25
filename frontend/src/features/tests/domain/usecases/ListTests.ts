import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestSummary } from '../entities/test'
import type { ITestRepository } from '../repositories/testRepository'

export class ListTests implements IUseCase<void, TestSummary[]> {
  private readonly repo: ITestRepository
  constructor(repo: ITestRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<TestSummary[]>> {
    return this.repo.list()
  }
}
