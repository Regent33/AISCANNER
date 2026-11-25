import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { TestOption } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

export class ListScanTests implements IUseCase<void, TestOption[]> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<TestOption[]>> {
    return this.repo.listTests()
  }
}
