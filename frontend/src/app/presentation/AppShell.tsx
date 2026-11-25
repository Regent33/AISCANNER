import { NavLink, Outlet } from 'react-router-dom'
import { Suspense } from 'react'
import { ChartBarIcon, ClipboardTextIcon, GearSixIcon, ListChecksIcon, ScanIcon, type Icon } from '@phosphor-icons/react'
import { ROUTES } from '@app/config/constants'
import { Skeleton } from '@shared/ui'
import { useHealth } from './useHealth'

const NAV: [string, string, Icon][] = [
  [ROUTES.tests, 'Tests', ClipboardTextIcon],
  [ROUTES.scan, 'Scan', ScanIcon],
  [ROUTES.review, 'Review', ListChecksIcon],
  [ROUTES.report, 'Report', ChartBarIcon],
  [ROUTES.settings, 'Settings', GearSixIcon],
]

export function AppShell() {
  const health = useHealth()
  return (
    <div className="flex min-h-[100dvh]">
      <nav aria-label="Main" className="sticky top-0 flex h-[100dvh] w-56 shrink-0 flex-col gap-1 border-r border-line bg-surface p-4">
        <div className="mb-6 px-3 text-lg font-semibold tracking-tight">Paper Scanner</div>
        {NAV.map(([to, label, Ico]) => (
          <NavLink key={to} to={to} end={to === ROUTES.tests}
            className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
              isActive ? 'bg-accent-soft text-ink' : 'text-muted hover:bg-bg hover:text-ink'}`}>
            <Ico size={20} weight="regular" aria-hidden />
            {label}
          </NavLink>
        ))}
        <p className="mt-auto px-3 text-xs text-muted" data-testid="health" role="status">{health}</p>
      </nav>
      <main className="min-w-0 flex-1">
        <Suspense fallback={<div className="p-10"><Skeleton className="h-8 w-48" /><Skeleton className="mt-6 h-40" /></div>}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
