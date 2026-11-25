import type { Result } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import type { Report, TestOption } from '../entities/report'

export interface IReportRepository {
  listTests(): Promise<Result<TestOption[]>>
  get(testId: TestId): Promise<Result<Report>>
  pdfUrl(testId: TestId): string
}
