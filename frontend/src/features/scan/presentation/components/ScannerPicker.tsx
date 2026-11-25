import { MagnifyingGlassIcon } from '@phosphor-icons/react'
import { Button, Field, Select, TextInput } from '@shared/ui'
import type { useScannerPicker } from '../viewmodels/useScannerPicker'

const KIND = { wia: 'USB or installed', escl: 'Network', sane: 'SANE' } as const

export function ScannerPicker({ p }: { p: ReturnType<typeof useScannerPicker> }) {
  return (
    <div className="grid gap-3">
      {p.devices.length > 0 ? (
        <Field label="Scanner">
          <Select value={p.chosen?.id ?? ''} onChange={(e) => p.choose(e.target.value)}
            options={p.devices.map((d) => ({ value: d.id, label: `${d.name} (${KIND[d.kind]})` }))} />
        </Field>
      ) : (
        <p className="text-sm text-muted" role="status">
          {p.searching ? 'Looking for scanners and printers...' : 'No scanner found. Check it is switched on and on the same network, or add a printer by its address.'}
        </p>
      )}
      <div className="flex flex-wrap items-end gap-2">
        <Button variant="quiet" onClick={p.search} disabled={p.searching}><MagnifyingGlassIcon size={18} aria-hidden /> Find scanners</Button>
        <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); p.addPrinter() }}>
          <div className="w-44"><Field label="Printer address"><TextInput value={p.address} placeholder="192.168.1.20"
            onChange={(e) => p.setAddress(e.target.value)} /></Field></div>
          <Button type="submit" disabled={p.adding || !p.address.trim()}>Add</Button>
        </form>
      </div>
      {p.error && <p className="text-sm text-danger" role="alert">{p.error}</p>}
    </div>
  )
}
