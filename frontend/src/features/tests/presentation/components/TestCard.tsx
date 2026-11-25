import { Link } from 'react-router-dom'
import { ROUTES } from '@app/config/constants'
import { Surface } from '@shared/ui'
import { plural } from '@shared/utils/format'
import type { TestSummary } from '../../domain/entities/test'

export function TestCard({ test, printUrl }: { test: TestSummary; printUrl: string }) {
  const facts = [
    test.subject || 'No subject',
    plural(test.questionCount, 'question'),
    plural(test.topicCount, 'topic'),
    test.pagesPerPaper ? plural(test.pagesPerPaper, 'page') : null,
  ].filter(Boolean)
  return (
    <Surface className="flex flex-wrap items-center justify-between gap-4">
      <div className="min-w-0">
        <h2 className="truncate font-medium">{test.name}</h2>
        <p className="text-sm text-muted">{facts.join(', ')}</p>
        {test.keylessCount > 0 && (
          <p className="mt-1 text-sm text-warn">{plural(test.keylessCount, 'question')} without an answer in the key</p>
        )}
        {!test.hasIdentityArea && <p className="mt-1 text-sm text-warn">Not printed from this app yet: use Print test</p>}
      </div>
      <div className="flex gap-2">
        {test.questionCount > 0 && (
          <a className="rounded-lg px-4 py-2 text-sm font-medium text-muted hover:bg-bg hover:text-ink" href={printUrl}
            download aria-label={`Print test: ${test.name}`}>Print test</a>
        )}
        <Link className="rounded-lg px-4 py-2 text-sm font-medium text-muted hover:bg-bg hover:text-ink" to={`/tests/${test.id}/edit`}
          aria-label={`Edit key or syllabus of ${test.name}`}>Edit</Link>
        <Link className="rounded-lg border border-control px-4 py-2 text-sm font-medium hover:bg-bg" to={`${ROUTES.scan}?test=${test.id}`}>Scan</Link>
        <Link className="rounded-lg border border-control px-4 py-2 text-sm font-medium hover:bg-bg" to={`${ROUTES.report}?test=${test.id}`}>Report</Link>
      </div>
    </Surface>
  )
}
