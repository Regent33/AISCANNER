import { container } from '@app/di/container'
import { TestRemoteDataSource } from '../data/datasources/remote/testRemoteDataSource'
import { TestRepositoryImpl } from '../data/repositories/testRepositoryImpl'
import { ListTests } from '../domain/usecases/ListTests'
import { CreateTest } from '../domain/usecases/CreateTest'
import { SetAnswerKey } from '../domain/usecases/SetAnswerKey'
import { SetSyllabus } from '../domain/usecases/SetSyllabus'
import { UploadSamplePage } from '../domain/usecases/UploadSamplePage'
import { SetIdentityArea } from '../domain/usecases/SetIdentityArea'

function build() {
  const repo = new TestRepositoryImpl(new TestRemoteDataSource(container.http))
  return {
    listTests: new ListTests(repo),
    createTest: new CreateTest(repo),
    setAnswerKey: new SetAnswerKey(repo),
    setSyllabus: new SetSyllabus(repo),
    uploadSamplePage: new UploadSamplePage(repo),
    setIdentityArea: new SetIdentityArea(repo),
    samplePageUrl: (id: Parameters<typeof repo.samplePageUrl>[0]) => repo.samplePageUrl(id),
    printableUrl: (id: Parameters<typeof repo.printableUrl>[0]) => repo.printableUrl(id),
    store: container.store,
  }
}

let mod: ReturnType<typeof build> | null = null
/** Feature injector: built on first use, when the route chunk loads. */
export const testsModule = () => (mod ??= build())
