import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { TextOrFile } from '../entities/test'
import type { ITestRepository } from '../repositories/testRepository'

type Input = { id: TestId; source: TextOrFile }

/** Returns the number of topics found. */
export class SetSyllabus implements IUseCase<Input, number> {
  private readonly repo: ITestRepository
  constructor(repo: ITestRepository) {
    this.repo = repo
  }

  async execute({ id, source }: Input): Promise<Result<number>> {
    if (source.kind === 'text' && !source.text.trim()) return err(new Failure('Paste the syllabus or choose a file.'))
    return this.repo.setSyllabus(id, source)
  }
}
