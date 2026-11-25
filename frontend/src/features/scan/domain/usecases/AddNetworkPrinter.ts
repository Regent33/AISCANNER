import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, type Result } from '@shared/kernel/types/result'
import type { ScannerDevice } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

/** A network printer-scanner the search did not find: checked by its IP address before it is offered. */
export class AddNetworkPrinter implements IUseCase<string, ScannerDevice> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  async execute(address: string): Promise<Result<ScannerDevice>> {
    if (!address.trim()) return err(new Failure("Type the printer's IP address, for example 192.168.1.20."))
    return this.repo.checkPrinter(address.trim())
  }
}
