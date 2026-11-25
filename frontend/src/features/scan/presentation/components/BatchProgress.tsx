import { Link } from 'react-router-dom'
import { PauseIcon, PlayIcon } from '@phosphor-icons/react'
import { ROUTES } from '@app/config/constants'
import { Banner, Button, Stat, Surface } from '@shared/ui'
import { eta } from '@shared/utils/format'
import type { Batch } from '../../domain/entities/batch'

const STATUS: Record<Batch['status'], string> = {
  queued: 'Waiting for pages', running: 'Working', paused: 'Paused', done: 'Finished', failed: 'Scanner error',
}

type Props = { batch: Batch; onPauseResume: () => void; onFinish: () => void }

export function BatchProgress({ batch: b, onPauseResume, onFinish }: Props) {
  const working = b.waitingJobs > 0
  return (
    <Surface className="grid gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-medium">Batch {b.id}: <span data-testid="batch-status">{STATUS[b.status]}</span></h2>
          <p className="text-sm text-muted">
            {b.watching ? `Watching ${b.watchFolder}. ` : ''}{working && b.status !== 'paused' ? `Time left: ${eta(b.etaSeconds)}.` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          {b.status !== 'done' && (
            <Button onClick={onPauseResume}>
              {b.status === 'paused' ? <><PlayIcon size={18} aria-hidden /> Resume</> : <><PauseIcon size={18} aria-hidden /> Pause</>}
            </Button>
          )}
          {!b.finished && <Button onClick={onFinish}>Last page is in</Button>}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Pages" value={b.pages} testId="stat-pages" />
        <Stat label="Papers found" value={b.papers} testId="stat-papers" />
        <Stat label="Papers graded" value={b.graded} testId="stat-graded" />
        <Stat label="Need a look" value={b.reviewPending} testId="stat-review" />
      </div>
      {b.lastError && <Banner tone="danger">{b.lastError}</Banner>}
      {b.failedJobs > 0 && <Banner tone="danger">{b.failedJobs} pages could not be processed. They are kept and flagged.</Banner>}
      {b.reviewPending > 0 && (
        <Link to={`${ROUTES.review}?test=${b.testId}&batch=${b.id}`} className="text-sm font-medium text-accent underline underline-offset-4">
          Review {b.reviewPending} items
        </Link>
      )}
    </Surface>
  )
}
