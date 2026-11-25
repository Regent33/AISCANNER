import type { TextOrFile } from '../../domain/entities/test'
import { Button, Field } from '@shared/ui'

type Props = { label: string; example: string; help: string; value: TextOrFile; onChange: (v: TextOrFile) => void }

export function TextOrFileInput({ label, example, help, value, onChange }: Props) {
  if (value.kind === 'file') {
    return (
      <div className="grid gap-2">
        <span className="text-sm font-medium">{label}</span>
        <div className="flex items-center gap-3 rounded-lg border border-line bg-bg px-4 py-3">
          <span className="truncate">{value.file.name}</span>
          <Button variant="quiet" onClick={() => onChange({ kind: 'text', text: '' })}>Paste text instead</Button>
        </div>
      </div>
    )
  }
  return (
    <div className="grid gap-4">
      <Field label={label} hint={help}>
        <textarea aria-label={label} value={value.text} spellCheck={false}
          onChange={(e) => onChange({ kind: 'text', text: e.target.value })}
          className="min-h-56 w-full rounded-lg border border-control bg-surface p-3 font-mono text-sm text-ink" />
      </Field>
      <details className="text-sm text-muted">
        <summary className="cursor-pointer">Show an example</summary>
        <pre className="mt-2 overflow-x-auto rounded-lg bg-bg p-3 font-mono">{example}</pre>
      </details>
      <Field label={`Or upload the ${label.toLowerCase()} (.txt or .pdf)`}>
        <input type="file" accept=".txt,.pdf,text/plain,application/pdf" aria-label={`${label} file`}
          className="text-sm file:mr-3 file:rounded-lg file:border file:border-control file:bg-surface file:px-3 file:py-1.5"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onChange({ kind: 'file', file: f }) }} />
      </Field>
    </div>
  )
}
