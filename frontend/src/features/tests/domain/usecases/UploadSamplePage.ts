import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { ITestRepository } from '../repositories/testRepository'

type Input = { id: TestId; file: File }

export class UploadSamplePage implements IUseCase<Input, void> {
  private readonly repo: ITestRepository
  constructor(repo: ITestRepository) {
    this.repo = repo
  }

  async execute({ id, file }: Input): Promise<Result<void>> {
    if (!file.type.startsWith('image/')) return err(new Failure('Choose an image of page 1 (PNG or JPG).'))
    return this.repo.uploadSamplePage(id, file)
  }
}
