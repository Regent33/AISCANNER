import { container } from '@app/di/container'
import { ReviewRemoteDataSource } from '../data/datasources/remote/reviewRemoteDataSource'
import { ReviewRepositoryImpl } from '../data/repositories/reviewRepositoryImpl'
import { ListReviewTests } from '../domain/usecases/ListReviewTests'
import { ListReviewBatches } from '../domain/usecases/ListReviewBatches'
import { GetReviewQueue } from '../domain/usecases/GetReviewQueue'
import { AcceptAnswer } from '../domain/usecases/AcceptAnswer'
import { ChangeScore } from '../domain/usecases/ChangeScore'
import { ConfirmIdentity } from '../domain/usecases/ConfirmIdentity'

function build() {
  const repo = new ReviewRepositoryImpl(new ReviewRemoteDataSource(container.http))
  return {
    listTests: new ListReviewTests(repo),
    listBatches: new ListReviewBatches(repo),
    getQueue: new GetReviewQueue(repo),
    acceptAnswer: new AcceptAnswer(repo),
    changeScore: new ChangeScore(repo),
    confirmIdentity: new ConfirmIdentity(repo),
    store: container.store,
  }
}

let mod: ReturnType<typeof build> | null = null
export const reviewModule = () => (mod ??= build())
