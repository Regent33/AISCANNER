import { Link } from 'react-router-dom'
import { ROUTES } from '@app/config/constants'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import { Banner, EmptyState, Field, Page, Select, Skeleton } from '@shared/ui'
import { plural } from '@shared/utils/format'
import { AnswerReview } from '../components/AnswerReview'
import { IdentityReview } from '../components/IdentityReview'
import { ReviewList } from '../components/ReviewList'
import { useReviewKeys } from '../viewmodels/useReviewKeys'
import { useReviewViewModel } from '../viewmodels/useReviewViewModel'

export default function ReviewPage() {
  const vm = useReviewViewModel()
  const cur = vm.current
  useReviewKeys({
    current: cur, next: vm.next, prev: vm.prev,
    accept: () => cur?.kind === 'answer' && vm.accept(cur),
    score: (n) => cur?.kind === 'answer' && n <= cur.maxPoints && vm.score(cur, n),
  })
  return (
    <Page title="Review" action={<span className="text-sm text-muted" data-testid="review-remaining">{plural(vm.total, 'item')} to check</span>}>
      <div className="grid gap-4 md:grid-cols-2 md:max-w-2xl">
        <Field label="Test"><Select value={vm.testId ?? ''} onChange={(e) => vm.setTestId(Number(e.target.value) as TestId)}
          options={vm.tests.map((t) => ({ value: t.id, label: t.name }))} /></Field>
        <Field label="Batch"><Select value={vm.batchId ?? ''} onChange={(e) => vm.setBatchId(Number(e.target.value) as BatchId)}
          options={vm.batches.map((b) => ({ value: b.id, label: b.name }))} /></Field>
      </div>
      {vm.error && <Banner tone="danger">{vm.error}</Banner>}
      {vm.loading && <Skeleton className="h-64" />}
      {!vm.loading && vm.batchId === null && <EmptyState title="Nothing scanned yet">Scan a batch of papers first.</EmptyState>}
      {!vm.loading && vm.batchId !== null && !cur && (
        <EmptyState title="Nothing left to check">
          Every answer in this batch was read confidently or has been checked. <Link className="text-accent underline" to={`${ROUTES.report}?test=${vm.testId}`}>See the report</Link>.
        </EmptyState>
      )}
      {cur && (
        <div className="grid gap-6 md:grid-cols-[16rem_1fr]">
          <ReviewList items={vm.items} index={vm.index} onSelect={vm.select} />
          <div className="grid content-start gap-3">
            {cur.kind === 'answer'
              ? <AnswerReview key={`a${cur.responseId}`} item={cur} onAccept={() => vm.accept(cur)} onScore={(n) => vm.score(cur, n)} />
              : <IdentityReview key={`p${cur.paperId}`} item={cur} onSave={(fix) => vm.confirmId(cur, fix)} />}
            <p className="text-sm text-muted">Keys: Enter accepts, 0 to 9 gives that score, J and K move down and up.</p>
          </div>
        </div>
      )}
    </Page>
  )
}
