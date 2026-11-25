import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import type { TestId } from '@shared/kernel/types/ids'
import { LAST_TEST_KEY, ROUTES } from '@app/config/constants'
import type { Box, TextOrFile } from '../../domain/entities/test'
import { testsModule } from '../../di/testsModule'
import { TESTS_QUERY } from './useTestsViewModel'

export const STEPS = ['Details', 'Answer key', 'Syllabus', 'Print'] as const
export type Details = { name: string; subject: string; pages: string }
const EMPTY: TextOrFile = { kind: 'text', text: '' }

const filled = (s: TextOrFile) => s.kind === 'file' || s.text.trim() !== ''

/** New test (all steps) or edit (editId: from the answer key on; an empty step keeps what the test has). */
export function useNewTestViewModel(editId: TestId | null = null) {
  const m = testsModule()
  const nav = useNavigate()
  const qc = useQueryClient()
  const editing = editId !== null
  const [step, setStep] = useState(editing ? 1 : 0)
  const [testId, setTestId] = useState<TestId | null>(editId)
  const [details, setDetails] = useState<Details>({ name: '', subject: '', pages: '' })
  const [key, setKey] = useState<TextOrFile>(EMPTY)
  const [syllabus, setSyllabus] = useState<TextOrFile>(EMPTY)
  const [box, setBox] = useState<Box | null>(null)
  const [sampleVersion, setSampleVersion] = useState(0)
  const [notice, setNotice] = useState<string | null>(null)
  const [printed, setPrinted] = useState(false)

  const advance = useMutation({
    mutationFn: async () => {
      if (step === 0 && testId === null) {
        const pages = details.pages.trim() ? Number(details.pages) : null
        setTestId(unwrap(await m.createTest.execute({ name: details.name, subject: details.subject, pagesPerPaper: pages })))
      } else if (step === 1 && filled(key)) {
        const k = unwrap(await m.setAnswerKey.execute({ id: testId!, source: key }))
        setNotice(`Found ${k.questions} questions.` + (k.keyless
          ? ` ${k.keyless} have no answer: the AI will work those out and the report will mark them as unverified.` : ''))
      } else if (step === 2 && filled(syllabus)) {
        const n = unwrap(await m.setSyllabus.execute({ id: testId!, source: syllabus }))
        setNotice(`Found ${n} topics.`)
      } else if (step === 3 && box) {
        unwrap(await m.setIdentityArea.execute({ id: testId!, box: box! }))
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TESTS_QUERY })
      if (step < STEPS.length - 1) return setStep(step + 1)
      m.store.set(LAST_TEST_KEY, testId)
      nav(editing ? ROUTES.tests : `${ROUTES.scan}?test=${testId}`)
    },
  })

  const uploadSample = useMutation({
    mutationFn: async (file: File) => unwrap(await m.uploadSamplePage.execute({ id: testId!, file })),
    onSuccess: () => { setBox(null); setSampleVersion((v) => v + 1) },
  })

  const canAdvance = editing ? step > 0 : [details.name.trim() !== '', filled(key), filled(syllabus), printed || box !== null][step]
  return {
    step, details, setDetails, key, setKey, syllabus, setSyllabus, box, setBox, notice,
    sampleUrl: testId !== null && sampleVersion > 0 ? `${m.samplePageUrl(testId)}?v=${sampleVersion}` : null,
    uploadSample: (f: File) => uploadSample.mutate(f),
    printUrl: testId !== null ? m.printableUrl(testId) : null,
    printed, markPrinted: () => { setPrinted(true); setSampleVersion((v) => v + 1) },
    editing, canGoBack: step > (editing ? 1 : 0),
    back: () => { setNotice(null); setStep(Math.max(editing ? 1 : 0, step - 1)) },
    next: () => { setNotice(null); advance.mutate() },
    canAdvance: canAdvance && !advance.isPending,
    error: (advance.error ?? uploadSample.error)?.message ?? null,
    isLast: step === STEPS.length - 1,
  }
}
