import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { Box } from '../entities/test'
import type { ITestRepository } from '../repositories/testRepository'

type Input = { id: TestId; box: Box }

/** The student details area (name, ID, year, section) is read on this computer only and blacked out before any other processing. */
export class SetIdentityArea implements IUseCase<Input, void> {
  private readonly repo: ITestRepository
  constructor(repo: ITestRepository) {
    this.repo = repo
  }

  async execute({ id, box }: Input): Promise<Result<void>> {
    const [x0, y0, x1, y1] = box
    if (x1 - x0 < 0.02 || y1 - y0 < 0.01) return err(new Failure('Drag a larger box over the student details area.'))
    return this.repo.setIdentityArea(id, box)
  }
}
