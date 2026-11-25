/** Shapes exactly as the API sends them (snake_case). */
export type TestDto = {
  id: number
  name: string
  subject: string
  pages_per_paper: number | null
  questions: number
  keyless_questions: number
  topics: number
  batches: number
  redaction_regions: RegionDto[]
}

export type RegionDto = { page: number; box: [number, number, number, number] }
export type NewTestDto = { name: string; subject: string; pages_per_paper: number | null }
export type KeyResultDto = { questions: number; keyless: number }
export type SyllabusResultDto = { topics: number }
