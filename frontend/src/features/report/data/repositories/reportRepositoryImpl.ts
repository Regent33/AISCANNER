import { map, type Result } from '@shared/kernel/types/result'
import { asId, type TestId } from '@shared/kernel/types/ids'
import type { IReportRepository } from '../../domain/repositories/reportRepository'
import type { Report, TestOption } from '../../domain/entities/report'
import { toReport } from '../mappers/reportMapper'
import type { ReportRemoteDataSource } from '../datasources/remote/reportRemoteDataSource'

export class ReportRepositoryImpl implements IReportRepository {
  private readonly remote: ReportRemoteDataSource
  constructor(remote: ReportRemoteDataSource) {
    this.remote = remote
  }

  async listTests(): Promise<Result<TestOption[]>> {
    return map(await this.remote.tests(), (ds) => ds.map((d) => ({ id: asId<TestId>(d.id), name: d.name })))
  }

  async get(testId: TestId): Promise<Result<Report>> {
    return map(await this.remote.report(testId), toReport)
  }

  pdfUrl(testId: TestId): string {
    return this.remote.pdfUrl(testId)
  }
}
