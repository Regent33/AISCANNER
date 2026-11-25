import type { ReactNode } from 'react'

/** Screen frame: title, optional single primary action, content. */
export function Page({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {action}
      </header>
      <div className="grid gap-6">{children}</div>
    </div>
  )
}
