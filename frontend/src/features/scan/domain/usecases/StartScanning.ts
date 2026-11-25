import type { IUseCase } from '@shared/kernel/contracts/usecase'
import { Failure, err, ok, type Result } from '@shared/kernel/types/result'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import type { Batch, ScanSource } from '../entities/batch'
import type { IBatchRepository } from '../repositories/batchRepository'

type Input = { testId: TestId; batchId: BatchId | null; source: ScanSource }

/** Starts the scanner or a folder watch, opening a new batch when there is no open one. */
export class StartScanning implements IUseCase<Input, Batch> {
  private readonly repo: IBatchRepository
  constructor(repo: IBatchRepository) {
    this.repo = repo
  }

  async execute({ testId, batchId, source }: Input): Promise<Result<Batch>> {
    if (source.kind === 'folder' && !source.folder.trim()) return err(new Failure('Type the folder the scanner saves into.'))
    const batch = batchId === null ? await this.repo.create(testId) : await this.repo.get(batchId)
    if (!batch.ok) return batch
    const started = await this.repo.startSource(batch.value.id, source)
    return started.ok ? ok(batch.value) : started
  }
}
