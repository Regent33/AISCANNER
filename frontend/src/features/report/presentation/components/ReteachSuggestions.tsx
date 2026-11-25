import { Surface } from '@shared/ui'
import type { Reteach } from '../../domain/entities/report'

export function ReteachSuggestions({ items }: { items: Reteach[] }) {
  if (items.length === 0) return null
  return (
    <Surface>
      <h2 className="mb-4 text-lg font-medium">Reteach suggestions</h2>
      <div className="grid gap-5 md:grid-cols-3" data-testid="reteach">
        {items.map((r) => (
          <div key={r.code} className="grid content-start gap-2">
            <h3 className="font-medium">{r.title}</h3>
            <ul className="grid list-disc gap-1 pl-5 text-sm text-muted">{r.activities.map((a) => <li key={a}>{a}</li>)}</ul>
          </div>
        ))}
      </div>
    </Surface>
  )
}
