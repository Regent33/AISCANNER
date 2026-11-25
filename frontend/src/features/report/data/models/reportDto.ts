export type ReportDto = {
  test: { id: number; name: string; subject: string }
  papers: number
  pending_review: number
  provisional: boolean
  topics: { code: string; title: string; miss_rate: number; points_missed: number; points_possible: number; questions: number[]; unverified: boolean }[]
  questions: {
    number: number; type: 'mcq' | 'written'; topic_title: string | null; miss_rate: number | null; responses: number
    key_source: 'key' | 'ai'; correct_answer: string | null; common_wrong: string | null
  }[]
  reteach: { code: string; title: string; activities: string[] }[]
}
