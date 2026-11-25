import type { Report } from '../../domain/entities/report'
import type { ReportDto } from '../models/reportDto'

export const toReport = (d: ReportDto): Report => ({
  testName: d.test.name,
  papers: d.papers,
  pendingReview: d.pending_review,
  provisional: d.provisional,
  topics: d.topics.map((t) => ({
    code: t.code, title: t.title, missRate: t.miss_rate, pointsMissed: t.points_missed,
    pointsPossible: t.points_possible, questions: t.questions, unverified: t.unverified,
  })),
  questions: d.questions.map((q) => ({
    number: q.number, type: q.type, topicTitle: q.topic_title, missRate: q.miss_rate, answered: q.responses,
    keyFromAi: q.key_source === 'ai', correctAnswer: q.correct_answer, commonWrong: q.common_wrong,
  })),
  reteach: d.reteach,
})
