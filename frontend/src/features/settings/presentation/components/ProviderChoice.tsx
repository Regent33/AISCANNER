import type { Provider } from '../../domain/entities/settings'

const OPTIONS: { value: Provider; title: string; body: string }[] = [
  { value: 'local', title: 'On this computer', body: 'Nothing leaves this computer. Works offline.' },
  { value: 'cloud', title: 'Cloud AI (Claude)', body: 'Use Claude through your Anthropic account.' },
  { value: 'openrouter', title: 'OpenRouter', body: 'Choose a model from the OpenRouter catalog.' },
  { value: 'nvidia', title: 'NVIDIA NIM', body: 'Use a hosted model from the NVIDIA API catalog.' },
]

export function ProviderChoice({ value, onChange }: { value: Provider; onChange: (p: Provider) => void }) {
  return (
    <fieldset className="grid gap-3 md:grid-cols-2">
      <legend className="mb-2 text-sm font-medium">Where the AI runs</legend>
      {OPTIONS.map((o) => (
        <label key={o.value} className={`grid cursor-pointer gap-1 rounded-lg border p-4 ${
          value === o.value ? 'border-accent bg-accent-soft' : 'border-line hover:bg-bg'}`}>
          <span className="flex items-center gap-2 font-medium">
            <input type="radio" name="provider" value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} className="accent-[var(--accent)]" />
            {o.title}
          </span>
          <span className="text-sm text-muted">{o.body}</span>
        </label>
      ))}
    </fieldset>
  )
}
