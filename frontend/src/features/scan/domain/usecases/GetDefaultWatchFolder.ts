import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { IBatchRepository } from '../repositories/batchRepository'

export class GetDefaultWatchFolder implements IUseCase<void, string> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<string>> {
    return this.repo.defaultWatchFolder()
  }
}
