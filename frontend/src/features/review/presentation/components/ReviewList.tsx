import { pct } from '@shared/utils/format'
import { itemKey, type ReviewItem } from '../../domain/entities/reviewItem'

type Props = { items: ReviewItem[]; index: number; onSelect: (i: number) => void }

export function ReviewList({ items, index, onSelect }: Props) {
  return (
    <ol className="grid max-h-[70dvh] content-start gap-1 overflow-y-auto pr-1" aria-label="Items to check">
      {items.map((it, i) => (
        <li key={itemKey(it)}>
          <button type="button" onClick={() => onSelect(i)} aria-current={i === index ? 'true' : undefined}
            className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm ${
              i === index ? 'bg-accent-soft text-ink' : 'text-muted hover:bg-bg'}`}>
            <span>{it.kind === 'answer' ? `Q${it.question}, ${it.studentRef ?? 'unknown'}` : `Student details, ${it.studentRef ?? 'paper'}`}</span>
            <span className="tabular-nums">{it.kind === 'answer' ? pct(it.confidence) : 'ID'}</span>
          </button>
        </li>
      ))}
    </ol>
  )
}
