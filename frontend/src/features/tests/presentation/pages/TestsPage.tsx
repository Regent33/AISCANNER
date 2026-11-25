import { Link } from 'react-router-dom'
import { ROUTES } from '@app/config/constants'
import { Banner, EmptyState, Page, Skeleton } from '@shared/ui'
import { TestCard } from '../components/TestCard'
import { useTestsViewModel } from '../viewmodels/useTestsViewModel'

const NEW = 'rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90'

export default function TestsPage() {
  const vm = useTestsViewModel()
  return (
    <Page title="Tests" action={<Link className={NEW} to={ROUTES.newTest}>New test</Link>}>
      {vm.error && <Banner tone="danger">{vm.error}</Banner>}
      {vm.loading && <><Skeleton className="h-20" /><Skeleton className="h-20" /></>}
      {!vm.loading && !vm.error && vm.tests.length === 0 && (
        <EmptyState title="No tests yet">Create a test with its answer key and syllabus, then scan the papers.</EmptyState>
      )}
      <div className="grid gap-3">{vm.tests.map((t) => <TestCard key={t.id} test={t} printUrl={vm.printUrl(t.id)} />)}</div>
    </Page>
  )
}
