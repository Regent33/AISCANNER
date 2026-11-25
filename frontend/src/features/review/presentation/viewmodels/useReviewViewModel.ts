import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import type { BatchId, TestId } from '@shared/kernel/types/ids'
import { useUrlSelection } from '@shared/utils/useUrlSelection'
import { LAST_TEST_KEY, REVIEW_PAGE_SIZE } from '@app/config/constants'
import { itemKey, type AnswerItem, type IdentityFix, type IdentityItem, type ReviewItem, type ReviewQueue } from '../../domain/entities/reviewItem'
import { reviewModule } from '../../di/reviewModule'

type Action =
  | { kind: 'accept'; item: AnswerItem }
  | { kind: 'score'; item: AnswerItem; score: number }
  | { kind: 'identity'; item: IdentityItem; fix: IdentityFix }

export function useReviewViewModel() {
  const m = reviewModule()
  const qc = useQueryClient()
  const tests = useQuery({ queryKey: ['review', 'tests'], queryFn: async () => unwrap(await m.listTests.execute()) })
  const [testId, setTestId] = useUrlSelection<TestId>('test', tests.data ?? [], m.store, LAST_TEST_KEY)
  const batches = useQuery({
    queryKey: ['review', 'batches', testId], enabled: testId !== null,
    queryFn: async () => unwrap(await m.listBatches.execute(testId!)),
  })
  const [batchId, setBatchId] = useUrlSelection<BatchId>('batch', batches.data ?? [], m.store, 'lastBatchId')
  const key = ['review', 'queue', batchId] as const
  const queue = useQuery({
    queryKey: key, enabled: batchId !== null,
    queryFn: async () => unwrap(await m.getQueue.execute({ batchId: batchId!, pageSize: REVIEW_PAGE_SIZE })),
  })
  const [index, setIndex] = useState(0)
  const items = queue.data?.items ?? []
  const at = Math.min(index, Math.max(0, items.length - 1))

  const resolve = useMutation({
    mutationFn: async (a: Action) => unwrap(
      a.kind === 'accept' ? await m.acceptAnswer.execute(a.item)
        : a.kind === 'score' ? await m.changeScore.execute({ item: a.item, score: a.score })
          : await m.confirmIdentity.execute({ item: a.item, fix: a.fix })),
    onMutate: async (a) => {  // optimistic: the next item shows at once, the server catches up
      await qc.cancelQueries({ queryKey: key })
      const before = qc.getQueryData<ReviewQueue>(key)
      qc.setQueryData<ReviewQueue>(key, (q) => q && { total: q.total - 1, items: q.items.filter((i) => itemKey(i) !== itemKey(a.item)) })
      return { before }
    },
    onError: (_e, _a, ctx) => ctx?.before && qc.setQueryData(key, ctx.before),
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  })

  const current: ReviewItem | null = items[at] ?? null
  return {
    tests: tests.data ?? [], testId, setTestId,
    batches: batches.data ?? [], batchId, setBatchId,
    loading: queue.isPending && batchId !== null, items, total: queue.data?.total ?? 0, index: at, current,
    select: setIndex,
    next: () => setIndex(Math.min(at + 1, items.length - 1)),
    prev: () => setIndex(Math.max(at - 1, 0)),
    accept: (item: AnswerItem) => resolve.mutate({ kind: 'accept', item }),
    score: (item: AnswerItem, score: number) => resolve.mutate({ kind: 'score', item, score }),
    confirmId: (item: IdentityItem, fix: IdentityFix) => resolve.mutate({ kind: 'identity', item, fix }),
    error: ([tests, batches, queue].find((q) => q.error)?.error ?? resolve.error)?.message ?? null,
  }
}
