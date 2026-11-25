import type { BatchId } from '@shared/kernel/types/ids'
import { Button } from '@shared/ui'
import type { Batch } from '../../domain/entities/batch'

type Props = { batches: Batch[]; current: BatchId | null; onPick: (id: BatchId) => void; onNew: () => void }

export function BatchHistory({ batches, current, onPick, onNew }: Props) {
  if (batches.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-muted">Batches:</span>
      {batches.map((b) => (
        <button key={b.id} type="button" onClick={() => onPick(b.id)} aria-pressed={b.id === current}
          className={`rounded-lg px-3 py-1 ${b.id === current ? 'bg-accent-soft text-ink' : 'text-muted hover:bg-bg'}`}>
          {b.id} ({b.papers} papers)
        </button>
      ))}
      <Button variant="quiet" onClick={onNew}>New batch</Button>
    </div>
  )
}
