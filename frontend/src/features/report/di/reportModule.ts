import { container } from '@app/di/container'
import type { TestId } from '@shared/kernel/types/ids'
import { ReportRemoteDataSource } from '../data/datasources/remote/reportRemoteDataSource'
import { ReportRepositoryImpl } from '../data/repositories/reportRepositoryImpl'
import { ListReportTests } from '../domain/usecases/ListReportTests'
import { GetReport } from '../domain/usecases/GetReport'

function build() {
  const repo = new ReportRepositoryImpl(new ReportRemoteDataSource(container.http))
  return {
    listTests: new ListReportTests(repo),
    getReport: new GetReport(repo),
    pdfUrl: (id: TestId) => repo.pdfUrl(id),
    store: container.store,
  }
}

let mod: ReturnType<typeof build> | null = null
export const reportModule = () => (mod ??= build())
