import { Link } from 'react-router-dom'
import { FilePdfIcon } from '@phosphor-icons/react'
import { ROUTES } from '@app/config/constants'
import type { TestId } from '@shared/kernel/types/ids'
import { Banner, EmptyState, Field, Page, Select, Skeleton } from '@shared/ui'
import { plural } from '@shared/utils/format'
import { QuestionTable } from '../components/QuestionTable'
import { ReteachSuggestions } from '../components/ReteachSuggestions'
import { WeakTopics } from '../components/WeakTopics'
import { useReportViewModel } from '../viewmodels/useReportViewModel'

const PDF = 'inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90'

export default function ReportPage() {
  const vm = useReportViewModel()
  const r = vm.report
  const pdf = vm.pdfUrl && r && r.papers > 0
    ? <a className={PDF} href={vm.pdfUrl} download><FilePdfIcon size={18} aria-hidden /> Export PDF</a> : undefined
  return (
    <Page title={r ? `Report: ${r.testName}` : 'Report'} action={pdf}>
      {vm.tests.length > 1 && (
        <div className="md:max-w-md"><Field label="Test"><Select value={vm.testId ?? ''}
          onChange={(e) => vm.setTestId(Number(e.target.value) as TestId)} options={vm.tests.map((t) => ({ value: t.id, label: t.name }))} /></Field></div>
      )}
      {vm.error && <Banner tone="danger">{vm.error}</Banner>}
      {(vm.testsLoading || vm.loading) && <><Skeleton className="h-48" /><Skeleton className="h-64" /></>}
      {!vm.testsLoading && vm.tests.length === 0 && <EmptyState title="No tests yet">Create a test and scan papers to see a report.</EmptyState>}
      {r && r.papers === 0 && <EmptyState title="No graded papers yet">Scan this test's papers and the report fills in as they are graded.</EmptyState>}
      {r && r.papers > 0 && (
        <>
          {r.provisional && (
            <Banner tone="warn">
              <span data-testid="provisional">Provisional: {plural(r.pendingReview, 'item')} still need a look. </span>
              <Link className="font-medium underline" to={`${ROUTES.review}?test=${vm.testId}`}>Review them</Link>
            </Banner>
          )}
          <p className="text-muted">{plural(r.papers, 'paper')} graded.</p>
          <WeakTopics topics={r.topics} />
          <ReteachSuggestions items={r.reteach} />
          <QuestionTable questions={r.questions} />
        </>
      )}
    </Page>
  )
}
