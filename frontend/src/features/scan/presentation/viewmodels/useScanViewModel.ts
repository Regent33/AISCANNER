import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import { useUrlSelection } from '@shared/utils/useUrlSelection'
import { LAST_TEST_KEY, POLL_MS } from '@app/config/constants'
import type { Batch, ScannerDevice, ScanSource } from '../../domain/entities/batch'
import { scanModule } from '../../di/scanModule'

const idle = (b: Batch | undefined) => !!b && (b.status === 'done' || (b.status === 'paused' && b.waitingJobs === 0))

export function useScanViewModel() {
  const m = scanModule()
  const qc = useQueryClient()
  const tests = useQuery({ queryKey: ['scan', 'tests'], queryFn: async () => unwrap(await m.listTests.execute()) })
  const [testId, setTestId] = useUrlSelection<TestId>('test', tests.data ?? [], m.store, LAST_TEST_KEY)
  const batches = useQuery({
    queryKey: ['batches', testId], enabled: testId !== null,
    queryFn: async () => unwrap(await m.listBatches.execute(testId!)),
  })
  const [chosen, setChosen] = useState<BatchId | 'new' | null>(null)
  const listed = chosen === 'new' ? undefined : batches.data?.find((b) => b.id === chosen) ?? batches.data?.[0]
  const live = useQuery({
    queryKey: ['batch', listed?.id], enabled: !!listed,
    queryFn: async () => unwrap(await m.getBatch.execute(listed!.id)),
    refetchInterval: (q) => (idle(q.state.data) ? false : POLL_MS),
  })
  const batch = live.data ?? listed ?? null
  const openId = batch && !batch.finished ? batch.id : null
  const folderDefault = useQuery({ queryKey: ['scan', 'folder'], queryFn: async () => unwrap(await m.defaultWatchFolder.execute()) })
  const [folder, setFolder] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const refresh = (b: Batch) => {
    setChosen(b.id)
    qc.setQueryData(['batch', b.id], b)
    qc.invalidateQueries({ queryKey: ['batches', testId] })
  }
  const start = useMutation({
    mutationFn: async (source: ScanSource) => unwrap(await m.startScanning.execute({ testId: testId!, batchId: openId, source })),
    onSuccess: (b, source) => { refresh(b); setNotice(source.kind === 'folder' ? 'Watching the folder. New scans appear here within a few seconds.' : `Scanning on ${source.device.name}. Pages appear here as they come in.`) },
  })
  const upload = useMutation({
    mutationFn: async (files: File[]) => unwrap(await m.uploadPages.execute({ testId: testId!, batchId: openId, files })),
    onSuccess: ({ batch: b, summary }) => {
      refresh(b)
      setNotice(`Added ${summary.added} pages.` + (summary.duplicates ? ` Skipped ${summary.duplicates} already added.` : ''))
    },
  })
  const pause = useMutation({ mutationFn: async (b: Batch) => unwrap(await m.pauseOrResume.execute(b)), onSuccess: refresh })
  const finish = useMutation({ mutationFn: async (id: BatchId) => unwrap(await m.finishBatch.execute(id)), onSuccess: refresh })
  const failure = [tests, batches, live].find((q) => q.error)?.error ?? start.error ?? upload.error ?? pause.error ?? finish.error

  return {
    tests: tests.data ?? [], testsLoading: tests.isPending, testId, setTestId: (id: TestId) => { setChosen(null); setTestId(id) },
    batches: batches.data ?? [], batch, chooseBatch: (id: BatchId) => setChosen(id), newBatch: () => setChosen('new'),
    folder: folder ?? folderDefault.data ?? '', setFolder,
    startScanner: (device: ScannerDevice) => start.mutate({ kind: 'scanner', device }),
    watchFolder: () => start.mutate({ kind: 'folder', folder: folder ?? folderDefault.data ?? '' }),
    upload: (files: File[]) => upload.mutate(files),
    pauseOrResume: () => batch && pause.mutate(batch),
    finish: () => batch && finish.mutate(batch.id),
    busy: start.isPending || upload.isPending,
    notice, error: failure?.message ?? null,
  }
}
