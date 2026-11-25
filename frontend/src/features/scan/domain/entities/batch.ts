import type { BatchId, TestId } from '@shared/kernel/types/ids'

export type BatchStatus = 'queued' | 'running' | 'paused' | 'done' | 'failed'

export type Batch = {
  id: BatchId
  testId: TestId
  status: BatchStatus
  pages: number
  papers: number
  graded: number
  flagged: number
  reviewPending: number
  waitingJobs: number
  failedJobs: number
  finished: boolean
  watching: boolean
  watchFolder: string | null
  etaSeconds: number | null
  lastError: string | null
  createdAt: string
}

export type TestOption = { id: TestId; name: string }
export type UploadSummary = { added: number; duplicates: number }
export type ScannerDevice = { kind: 'wia' | 'escl' | 'sane'; id: string; name: string }
export type ScanSource = { kind: 'scanner'; device: ScannerDevice } | { kind: 'folder'; folder: string }
