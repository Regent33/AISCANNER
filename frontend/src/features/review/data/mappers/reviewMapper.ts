import { asId } from '@shared/kernel/types/ids'
import type { ReviewItem } from '../../domain/entities/reviewItem'
import type { IdentityItemDto, ResponseItemDto } from '../models/reviewDto'

const PROBLEMS: Record<string, string> = {
  id_unreadable: 'The student ID could not be read.',
  id_low_confidence: 'The student ID is unclear.',
  id_duplicate: 'Another paper has the same student ID.',
  id_no_region: 'The student details area is not set for this test.',
}

function mcqReading(a: string | null) {
  if (a === 'MULTI') return 'More than one bubble filled'
  return a ? `Filled ${a}` : 'Nothing filled'
}

type Urls = { crop: (responseId: number) => string; identity: (paperId: number) => string }

export function toReviewItem(d: IdentityItemDto | ResponseItemDto, urls: Urls): ReviewItem {
  if (d.kind === 'identity') {
    const problem = d.flags.map((f) => PROBLEMS[f]).find(Boolean) ?? 'Check the student ID.'
    return { kind: 'identity', paperId: asId(d.paper_id), studentRef: d.student_ref, readId: d.read_id, year: d.year, section: d.section, problem,
      imageUrl: urls.identity(d.paper_id) }
  }
  return {
    kind: 'answer', responseId: asId(d.response_id), paperId: asId(d.paper_id), studentRef: d.student_ref,
    question: d.question, type: d.type, maxPoints: d.max_points, correctAnswer: d.correct_answer,
    keyFromAi: d.key_source === 'ai', score: d.score, confidence: d.confidence, imageUrl: urls.crop(d.response_id),
    reading: d.type === 'mcq' ? mcqReading(d.normalized_answer) : d.raw_read?.trim() || '(blank)',
  }
}
