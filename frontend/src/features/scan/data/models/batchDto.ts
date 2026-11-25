export type BatchDto = {
  id: number
  test_id: number
  status: 'queued' | 'running' | 'paused' | 'done' | 'failed'
  total_pages: number
  total_papers: number
  papers_graded: number
  papers_flagged: number
  review_pending: number
  jobs: Record<string, number>
  finished: number
  watching: boolean
  watch_folder: string | null
  eta_seconds: number | null
  last_error: string | null
  created_at: string
}

export type TestOptionDto = { id: number; name: string }
export type UploadDto = { added: number; duplicates: number }
export type ScannerDto = { kind: 'wia' | 'escl' | 'sane'; id: string; name: string }
export type ScanRequestDto = { mode: 'watch' | 'scanner'; device?: ScannerDto['kind']; target?: string; folder?: string }
