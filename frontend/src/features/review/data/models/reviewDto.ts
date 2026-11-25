export type IdentityItemDto = {
  kind: 'identity'
  paper_id: number
  student_ref: string | null
  read_id: string | null
  year: string | null
  section: string | null
  confidence: number | null
  flags: string[]
}

export type ResponseItemDto = {
  kind: 'response'
  response_id: number
  paper_id: number
  student_ref: string | null
  question: number
  type: 'mcq' | 'written'
  max_points: number
  correct_answer: string | null
  key_source: 'key' | 'ai'
  raw_read: string | null
  normalized_answer: string | null
  score: number | null
  confidence: number
}

export type ReviewQueueDto = { total: number; items: (IdentityItemDto | ResponseItemDto)[] }
export type NamedDto = { id: number; name?: string; total_papers?: number; created_at?: string }
