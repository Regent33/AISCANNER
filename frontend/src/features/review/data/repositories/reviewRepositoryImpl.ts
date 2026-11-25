import { map, type Result } from '@shared/kernel/types/result'
import { asId, type BatchId, type PaperId, type ResponseId, type TestId } from '@shared/kernel/types/ids'
import type { IReviewRepository } from '../../domain/repositories/reviewRepository'
import type { BatchOption, IdentityFix, ReviewQueue, TestOption } from '../../domain/entities/reviewItem'
import { toReviewItem } from '../mappers/reviewMapper'
import type { ReviewRemoteDataSource } from '../datasources/remote/reviewRemoteDataSource'

export class ReviewRepositoryImpl implements IReviewRepository {
  private readonly remote: ReviewRemoteDataSource
  constructor(remote: ReviewRemoteDataSource) {
    this.remote = remote
  }

  async listTests(): Promise<Result<TestOption[]>> {
    return map(await this.remote.tests(), (ds) => ds.map((d) => ({ id: asId<TestId>(d.id), name: d.name ?? `Test ${d.id}` })))
  }

  async listBatches(testId: TestId): Promise<Result<BatchOption[]>> {
    return map(await this.remote.batches(testId), (ds) =>
      ds.map((d) => ({ id: asId<BatchId>(d.id), name: `Batch ${d.id} (${d.total_papers ?? 0} papers)` })))
  }

  async queue(batchId: BatchId, pageSize: number): Promise<Result<ReviewQueue>> {
    const urls = { crop: this.remote.cropUrl, identity: this.remote.identityUrl }
    return map(await this.remote.queue(batchId, pageSize), (q) => ({ total: q.total, items: q.items.map((i) => toReviewItem(i, urls)) }))
  }

  async setScore(id: ResponseId, score: number | null): Promise<Result<void>> {
    return map(await this.remote.patchResponse(id, score), () => undefined)
  }

  async setIdentity(id: PaperId, fix: IdentityFix): Promise<Result<void>> {
    return map(await this.remote.patchPaper(id, { student_id: fix.studentId, year: fix.year, section: fix.section }), () => undefined)
  }
}
