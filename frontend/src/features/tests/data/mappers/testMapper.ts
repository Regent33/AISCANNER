import { asId } from '@shared/kernel/types/ids'
import type { NewTest, TestSummary } from '../../domain/entities/test'
import type { NewTestDto, TestDto } from '../models/testDto'

export const toTestSummary = (d: TestDto): TestSummary => ({
  id: asId(d.id),
  name: d.name,
  subject: d.subject,
  pagesPerPaper: d.pages_per_paper,
  questionCount: d.questions,
  keylessCount: d.keyless_questions,
  topicCount: d.topics,
  batchCount: d.batches,
  hasIdentityArea: d.redaction_regions.length > 0,
})

export const toNewTestDto = (t: NewTest): NewTestDto => ({ name: t.name, subject: t.subject, pages_per_paper: t.pagesPerPaper })
