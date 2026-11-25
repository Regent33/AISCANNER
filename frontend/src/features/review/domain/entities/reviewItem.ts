import type { BatchId, PaperId, ResponseId, TestId } from '@shared/kernel/types/ids'

export type IdentityItem = {
  kind: 'identity'
  paperId: PaperId
  studentRef: string | null
  readId: string | null
  year: string | null
  section: string | null
  problem: string
  imageUrl: string
}

export type AnswerItem = {
  kind: 'answer'
  responseId: ResponseId
  paperId: PaperId
  studentRef: string | null
  question: number
  type: 'mcq' | 'written'
  maxPoints: number
  correctAnswer: string | null
  keyFromAi: boolean
  reading: string
  score: number | null
  confidence: number
  imageUrl: string
}

export type IdentityFix = { studentId: string; year: string; section: string }

export type ReviewItem = IdentityItem | AnswerItem
export type ReviewQueue = { total: number; items: ReviewItem[] }
export type Option<I> = { id: I; name: string }
export type TestOption = Option<TestId>
export type BatchOption = Option<BatchId>

export const itemKey = (i: ReviewItem) => (i.kind === 'answer' ? `a${i.responseId}` : `p${i.paperId}`)
