import { useQuery } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import { useUrlSelection } from '@shared/utils/useUrlSelection'
import { LAST_TEST_KEY } from '@app/config/constants'
import { reportModule } from '../../di/reportModule'

export function useReportViewModel() {
  const m = reportModule()
  const tests = useQuery({ queryKey: ['report', 'tests'], queryFn: async () => unwrap(await m.listTests.execute()) })
  const [testId, setTestId] = useUrlSelection<TestId>('test', tests.data ?? [], m.store, LAST_TEST_KEY)
  const report = useQuery({
    queryKey: ['report', testId], enabled: testId !== null,
    queryFn: async () => unwrap(await m.getReport.execute(testId!)),
  })
  const r = report.data
  return {
    tests: tests.data ?? [], testsLoading: tests.isPending, testId, setTestId,
    report: r ?? null, loading: report.isPending && testId !== null,
    pdfUrl: testId !== null ? m.pdfUrl(testId) : null,
    error: (tests.error ?? report.error)?.message ?? null,
  }
}
