/** App-wide constants. Never inline these values elsewhere. */
export const API_BASE = '/api'
export const POLL_MS = 1500
export const HEALTH_POLL_MS = 10_000
export const REVIEW_PAGE_SIZE = 50
export const STORE_NAMESPACE = 'paper-scanner'

export const ROUTES = {
  tests: '/tests',
  newTest: '/tests/new',
  editTest: '/tests/:id/edit',
  scan: '/scan',
  review: '/review',
  report: '/report',
  settings: '/settings',
} as const

/** Remembered selection shared by Scan, Review and Report (a UI preference, not student data). */
export const LAST_TEST_KEY = 'lastTestId'
