import { asId } from '@shared/kernel/types/ids'
import type { Batch, ScanSource, TestOption } from '../../domain/entities/batch'
import type { BatchDto, ScanRequestDto, TestOptionDto } from '../models/batchDto'

export const toBatch = (d: BatchDto): Batch => ({
  id: asId(d.id),
  testId: asId(d.test_id),
  status: d.status,
  pages: d.total_pages,
  papers: d.total_papers,
  graded: d.papers_graded,
  flagged: d.papers_flagged,
  reviewPending: d.review_pending,
  waitingJobs: (d.jobs.queued ?? 0) + (d.jobs.running ?? 0),
  failedJobs: d.jobs.failed ?? 0,
  finished: d.finished === 1,
  watching: d.watching,
  watchFolder: d.watch_folder,
  etaSeconds: d.eta_seconds,
  lastError: d.last_error,
  createdAt: d.created_at,
})

export const toTestOption = (d: TestOptionDto): TestOption => ({ id: asId(d.id), name: d.name })

export const toScanRequest = (s: ScanSource): ScanRequestDto =>
  s.kind === 'scanner' ? { mode: 'scanner', device: s.device.kind, target: s.device.id } : { mode: 'watch', folder: s.folder.trim() }
