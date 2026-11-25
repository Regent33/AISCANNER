import { defineConfig } from '@playwright/test'
import path from 'node:path'

export const ROOT = path.resolve(import.meta.dirname, '..')
export const PY = path.join(ROOT, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
// A fresh data folder per run (workers inherit the env var, so they agree on it).
process.env.E2E_DATA ??= path.join(ROOT, 'data', 'e2e', String(Date.now()))
export const DATA = process.env.E2E_DATA

export default defineConfig({
  testDir: 'e2e',
  timeout: 120_000,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8765', channel: 'msedge', headless: true, acceptDownloads: true },
  webServer: {
    command: `"${PY}" -m uvicorn app.main:app --app-dir "${path.join(ROOT, 'backend')}" --port 8765 --log-level warning`,
    url: 'http://127.0.0.1:8765/api/health',
    reuseExistingServer: false,
    env: { SCANNER_DATA: DATA },
  },
})
