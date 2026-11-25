import { Button, Surface } from '@shared/ui'
import { pct } from '@shared/utils/format'
import type { AnswerItem } from '../../domain/entities/reviewItem'

type Props = { item: AnswerItem; onAccept: () => void; onScore: (n: number) => void }

export function AnswerReview({ item, onAccept, onScore }: Props) {
  const points = Array.from({ length: item.maxPoints + 1 }, (_, i) => i)
  return (
    <Surface className="grid gap-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-medium">Question {item.question}</h2>
        <span className="text-sm text-muted">{item.studentRef}, AI confidence {pct(item.confidence)}</span>
      </div>
      <img src={item.imageUrl} alt={`Answer to question ${item.question} (name area blacked out)`}
        className="w-full rounded-lg border border-line bg-white" />
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt className="text-muted">AI read</dt><dd className="font-medium" data-testid="ai-reading">{item.reading}</dd></div>
        <div>
          <dt className="text-muted">Answer key</dt>
          <dd className="font-medium">{item.correctAnswer ?? 'none'}{item.keyFromAi && <span className="text-warn"> (AI, unverified)</span>}</dd>
        </div>
        <div><dt className="text-muted">AI score</dt><dd className="font-medium">{item.score ?? 'n/a'} of {item.maxPoints}</dd></div>
      </dl>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="primary" onClick={onAccept} disabled={item.score === null}>Accept AI score</Button>
        <span className="px-2 text-sm text-muted">or give</span>
        {points.map((p) => (
          <Button key={p} onClick={() => onScore(p)} aria-label={`Give ${p} points`} className="min-w-11">{p}</Button>
        ))}
      </div>
    </Surface>
  )
}
