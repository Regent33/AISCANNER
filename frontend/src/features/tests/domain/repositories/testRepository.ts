import type { Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { Box, KeySummary, NewTest, TestSummary, TextOrFile } from '../entities/test'

export interface ITestRepository {
  list(): Promise<Result<TestSummary[]>>
  create(test: NewTest): Promise<Result<TestId>>
  setAnswerKey(id: TestId, source: TextOrFile): Promise<Result<KeySummary>>
  setSyllabus(id: TestId, source: TextOrFile): Promise<Result<number>>
  uploadSamplePage(id: TestId, file: File): Promise<Result<void>>
  samplePageUrl(id: TestId): string
  printableUrl(id: TestId): string
  setIdentityArea(id: TestId, box: Box): Promise<Result<void>>
}
