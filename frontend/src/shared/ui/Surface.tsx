import type { ReactNode } from 'react'

export function Surface({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-lg border border-line bg-surface p-5 ${className}`}>{children}</section>
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Surface className="py-12 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mx-auto mt-2 max-w-[60ch] text-muted">{children}</div>}
    </Surface>
  )
}

export function Banner({ tone, children }: { tone: 'warn' | 'danger' | 'info'; children: ReactNode }) {
  const cls = { warn: 'bg-warn-soft text-warn', danger: 'bg-danger-soft text-danger', info: 'bg-accent-soft text-ink' }[tone]
  return <div role={tone === 'danger' ? 'alert' : 'status'} className={`rounded-lg px-4 py-3 text-sm ${cls}`}>{children}</div>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-line/60 ${className}`} />
}
