import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { NewTest } from '../entities/test'
import type { ITestRepository } from '../repositories/testRepository'

export class CreateTest implements IUseCase<NewTest, TestId> {
  private readonly repo: ITestRepository
  constructor(repo: ITestRepository) {
    this.repo = repo
  }

  async execute(input: NewTest): Promise<Result<TestId>> {
    if (!input.name.trim()) return err(new Failure('Give the test a name.'))
    const p = input.pagesPerPaper
    if (p !== null && (!Number.isInteger(p) || p < 1)) return err(new Failure('Pages per paper must be a whole number, 1 or more.'))
    return this.repo.create({ ...input, name: input.name.trim() })
  }
}
