import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import type { Settings } from '../../domain/entities/settings'
import { settingsModule } from '../../di/settingsModule'

export function useSettingsViewModel() {
  const m = settingsModule()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['settings'], queryFn: async () => unwrap(await m.getSettings.execute()) })
  const [draft, setDraft] = useState<Settings | null>(null)
  const form = draft ?? q.data ?? null
  const save = useMutation({
    mutationFn: async (s: Settings) => unwrap(await m.saveSettings.execute(s)),
    onSuccess: (s) => { qc.setQueryData(['settings'], s); setDraft(null) },
  })
  return {
    form, loading: q.isPending,
    update: (patch: Partial<Settings>) => form && setDraft({ ...form, ...patch }),
    dirty: draft !== null,
    save: () => form && save.mutate(form),
    saving: save.isPending,
    saved: save.isSuccess && draft === null,
    error: (q.error ?? save.error)?.message ?? null,
  }
}
