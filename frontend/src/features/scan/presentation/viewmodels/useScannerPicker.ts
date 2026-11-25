import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { unwrap } from '@shared/kernel/types/result'
import type { ScannerDevice } from '../../domain/entities/batch'
import { scanModule } from '../../di/scanModule'

const MANUAL_KEY = 'manualPrinters'
const CHOSEN_KEY = 'scannerId'

/** Found scanners plus printers added by address (remembered), and the one the teacher picked. */
export function useScannerPicker() {
  const m = scanModule()
  const found = useQuery({ queryKey: ['scanners'], queryFn: async () => unwrap(await m.findScanners.execute()), staleTime: Infinity })
  const [manual, setManual] = useState<ScannerDevice[]>(() => m.store.get<ScannerDevice[]>(MANUAL_KEY, []))
  const [chosenId, setChosenId] = useState<string | null>(() => m.store.get<string | null>(CHOSEN_KEY, null))
  const [address, setAddress] = useState('')
  const devices = [...(found.data ?? []), ...manual.filter((d) => !found.data?.some((f) => f.id === d.id))]
  const chosen = devices.find((d) => d.id === chosenId) ?? devices[0] ?? null

  const choose = (id: string) => { setChosenId(id); m.store.set(CHOSEN_KEY, id) }
  const add = useMutation({
    mutationFn: async (a: string) => unwrap(await m.addNetworkPrinter.execute(a)),
    onSuccess: (d) => {
      const next = [...manual.filter((x) => x.id !== d.id), d]
      setManual(next); m.store.set(MANUAL_KEY, next); choose(d.id); setAddress('')
    },
  })
  return {
    devices, chosen, choose, searching: found.isFetching, search: () => found.refetch(),
    address, setAddress, addPrinter: () => add.mutate(address), adding: add.isPending,
    error: (found.error ?? add.error)?.message ?? null,
  }
}
