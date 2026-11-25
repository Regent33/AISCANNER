import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ROUTES } from '@app/config/constants'
import { AppShell } from './AppShell'

// Each feature (and its DI module) loads on first entry to its route.
const TestsPage = lazy(() => import('@features/tests/presentation/pages/TestsPage'))
const NewTestPage = lazy(() => import('@features/tests/presentation/pages/NewTestPage'))
const ScanPage = lazy(() => import('@features/scan/presentation/pages/ScanPage'))
const ReviewPage = lazy(() => import('@features/review/presentation/pages/ReviewPage'))
const ReportPage = lazy(() => import('@features/report/presentation/pages/ReportPage'))
const SettingsPage = lazy(() => import('@features/settings/presentation/pages/SettingsPage'))

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to={ROUTES.tests} replace />} />
        <Route path={ROUTES.tests} element={<TestsPage />} />
        <Route path={ROUTES.newTest} element={<NewTestPage />} />
        <Route path={ROUTES.editTest} element={<NewTestPage />} />
        <Route path={ROUTES.scan} element={<ScanPage />} />
        <Route path={ROUTES.review} element={<ReviewPage />} />
        <Route path={ROUTES.report} element={<ReportPage />} />
        <Route path={ROUTES.settings} element={<SettingsPage />} />
        <Route path="*" element={<Navigate to={ROUTES.tests} replace />} />
      </Route>
    </Routes>
  )
}
