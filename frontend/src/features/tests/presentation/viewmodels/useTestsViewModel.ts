import { useQuery } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import { testsModule } from '../../di/testsModule'

export const TESTS_QUERY = ['tests'] as const

export function useTestsViewModel() {
  const m = testsModule()
  const q = useQuery({ queryKey: TESTS_QUERY, queryFn: async () => unwrap(await m.listTests.execute()) })
  return { tests: q.data ?? [], loading: q.isPending, error: q.error?.message ?? null, printUrl: m.printableUrl }
}
