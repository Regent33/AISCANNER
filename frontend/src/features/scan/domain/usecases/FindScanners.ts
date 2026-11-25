import type { IUseCase } from '@shared/kernel/contracts/usecase'
import type { Result } from '@shared/kernel/types/result'
import type { ScannerDevice } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

/** Every scanner this computer can reach: Windows drivers, network printers (AirScan/Mopria), SANE. */
export class FindScanners implements IUseCase<void, ScannerDevice[]> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  execute(): Promise<Result<ScannerDevice[]>> {
    return this.repo.findScanners()
  }
}
