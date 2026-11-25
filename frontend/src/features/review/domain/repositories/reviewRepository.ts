import type { Result } from '@shared/kernel/types/result'
import type { BatchId, PaperId, ResponseId, TestId } from '@shared/kernel/types/ids'
import type { BatchOption, IdentityFix, ReviewQueue, TestOption } from '../entities/reviewItem'

export interface IReviewRepository {
  listTests(): Promise<Result<TestOption[]>>
  listBatches(testId: TestId): Promise<Result<BatchOption[]>>
  queue(batchId: BatchId, pageSize: number): Promise<Result<ReviewQueue>>
  setScore(id: ResponseId, score: number | null): Promise<Result<void>>
  setIdentity(id: PaperId, fix: IdentityFix): Promise<Result<void>>
}
