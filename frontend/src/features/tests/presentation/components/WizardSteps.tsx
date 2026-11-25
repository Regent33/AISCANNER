export function WizardSteps({ steps, current }: { steps: readonly string[]; current: number }) {
  return (
    <ol className="flex flex-wrap gap-2 text-sm" aria-label="Steps">
      {steps.map((s, i) => (
        <li key={s} aria-current={i === current ? 'step' : undefined}
          className={`rounded-lg px-3 py-1.5 ${i === current ? 'bg-accent text-accent-ink'
            : i < current ? 'bg-accent-soft text-ink' : 'border border-line text-muted'}`}>
          {i + 1}. {s}
        </li>
      ))}
    </ol>
  )
}
