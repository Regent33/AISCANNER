import { Surface } from '@shared/ui'
import { pct } from '@shared/utils/format'
import type { TopicStat } from '../../domain/entities/report'

export function WeakTopics({ topics }: { topics: TopicStat[] }) {
  return (
    <Surface>
      <h2 className="mb-4 text-lg font-medium">Topics to reinforce</h2>
      <ol className="grid gap-4" data-testid="weak-topics">
        {topics.map((t, i) => (
          <li key={t.code} className="grid gap-1">
            <div className="flex items-baseline justify-between gap-3">
              <span className={i < 3 ? 'font-medium' : ''}>{i + 1}. {t.title}{t.unverified && <span className="text-sm text-warn"> (uses AI answers)</span>}</span>
              <span className="tabular-nums text-muted">{pct(t.missRate)} missed</span>
            </div>
            <div aria-hidden className={`h-1.5 rounded-lg ${i < 3 ? 'bg-accent' : 'bg-muted/40'}`} style={{ width: `${Math.max(2, t.missRate * 100)}%` }} />
            <span className="text-sm text-muted">Questions {t.questions.join(', ')}. {t.pointsMissed} of {t.pointsPossible} points lost.</span>
          </li>
        ))}
      </ol>
    </Surface>
  )
}
