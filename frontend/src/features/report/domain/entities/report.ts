import type { TestId } from '@shared/kernel/types/ids'

export type TopicStat = {
  code: string
  title: string
  missRate: number
  pointsMissed: number
  pointsPossible: number
  questions: number[]
  unverified: boolean
}

export type QuestionStat = {
  number: number
  type: 'mcq' | 'written'
  topicTitle: string | null
  missRate: number | null
  answered: number
  keyFromAi: boolean
  correctAnswer: string | null
  commonWrong: string | null
}

export type Reteach = { code: string; title: string; activities: string[] }

export type Report = {
  testName: string
  papers: number
  pendingReview: number
  provisional: boolean
  topics: TopicStat[]
  questions: QuestionStat[]
  reteach: Reteach[]
}

export type TestOption = { id: TestId; name: string }
