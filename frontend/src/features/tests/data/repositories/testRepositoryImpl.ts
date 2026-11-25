import { map, type Result } from '@shared/kernel/types/result'
import { asId, type TestId } from '@shared/kernel/types/ids'
import type { ITestRepository } from '../../domain/repositories/testRepository'
import type { Box, KeySummary, NewTest, TestSummary, TextOrFile } from '../../domain/entities/test'
import type { KeyResultDto, SyllabusResultDto } from '../models/testDto'
import { toNewTestDto, toTestSummary } from '../mappers/testMapper'
import type { TestRemoteDataSource } from '../datasources/remote/testRemoteDataSource'

export class TestRepositoryImpl implements ITestRepository {
  private readonly remote: TestRemoteDataSource
  constructor(remote: TestRemoteDataSource) {
    this.remote = remote
  }

  async list(): Promise<Result<TestSummary[]>> {
    return map(await this.remote.list(), (ds) => ds.map(toTestSummary))
  }

  async create(test: NewTest): Promise<Result<TestId>> {
    return map(await this.remote.create(toNewTestDto(test)), (d) => asId<TestId>(d.id))
  }

  async setAnswerKey(id: TestId, src: TextOrFile): Promise<Result<KeySummary>> {
    const r = src.kind === 'text'
      ? await this.remote.sendText<KeyResultDto>(id, 'key', src.text)
      : await this.remote.sendFile<KeyResultDto>(id, 'key', src.file)
    return map(r, (d) => ({ questions: d.questions, keyless: d.keyless }))
  }

  async setSyllabus(id: TestId, src: TextOrFile): Promise<Result<number>> {
    const r = src.kind === 'text'
      ? await this.remote.sendText<SyllabusResultDto>(id, 'syllabus', src.text)
      : await this.remote.sendFile<SyllabusResultDto>(id, 'syllabus', src.file)
    return map(r, (d) => d.topics)
  }

  async uploadSamplePage(id: TestId, file: File): Promise<Result<void>> {
    return map(await this.remote.uploadSample(id, file), () => undefined)
  }

  samplePageUrl(id: TestId): string {
    return this.remote.sampleUrl(id)
  }

  printableUrl(id: TestId): string {
    return this.remote.printableUrl(id)
  }

  async setIdentityArea(id: TestId, box: Box): Promise<Result<void>> {
    return map(await this.remote.setRegions(id, [{ page: 1, box }]), () => undefined)
  }
}
