import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { KeySummary, TextOrFile } from '../entities/test'
import type { ITestRepository } from '../repositories/testRepository'

type Input = { id: TestId; source: TextOrFile }

export class SetAnswerKey implements IUseCase<Input, KeySummary> {
  private readonly repo: ITestRepository
  constructor(repo: ITestRepository) {
    this.repo = repo
  }

  async execute({ id, source }: Input): Promise<Result<KeySummary>> {
    if (source.kind === 'text' && !source.text.trim()) return err(new Failure('Paste the answer key or choose a file.'))
    return this.repo.setAnswerKey(id, source)
  }
}
