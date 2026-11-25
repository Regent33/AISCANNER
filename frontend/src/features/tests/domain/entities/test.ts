import type { TestId } from '@shared/kernel/types/ids'

export type TestSummary = {
  id: TestId
  name: string
  subject: string
  pagesPerPaper: number | null
  questionCount: number
  keylessCount: number
  topicCount: number
  batchCount: number
  hasIdentityArea: boolean
}

export type NewTest = { name: string; subject: string; pagesPerPaper: number | null }

/** Key and syllabus arrive either pasted or as a file (.txt / .pdf). */
export type TextOrFile = { kind: 'text'; text: string } | { kind: 'file'; file: File }

/** Normalised [x0, y0, x1, y1] on page 1, 0..1. */
export type Box = [number, number, number, number]

export type KeySummary = { questions: number; keyless: number }
