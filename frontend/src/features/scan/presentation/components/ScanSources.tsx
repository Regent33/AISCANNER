import { FolderOpenIcon, ScanIcon, UploadSimpleIcon } from '@phosphor-icons/react'
import { Button, Field, Surface, TextInput } from '@shared/ui'
import type { ScannerDevice } from '../../domain/entities/batch'
import { useScannerPicker } from '../viewmodels/useScannerPicker'
import { ScannerPicker } from './ScannerPicker'

type Props = {
  folder: string; setFolder: (f: string) => void; busy: boolean
  onScanner: (device: ScannerDevice) => void; onWatch: () => void; onUpload: (files: File[]) => void
}

/** The three ways pages get in. The scanner is the main one. */
export function ScanSources({ folder, setFolder, busy, onScanner, onWatch, onUpload }: Props) {
  const picker = useScannerPicker()
  return (
    <Surface className="grid gap-6 md:grid-cols-[1fr_1fr]">
      <div className="grid content-start gap-3">
        <h2 className="font-medium">Scanner</h2>
        <p className="text-sm text-muted">Put the papers in the feeder (or one page on the glass), page 1 first, then press Start.</p>
        <ScannerPicker p={picker} />
        <Button variant="primary" disabled={busy || !picker.chosen} onClick={() => picker.chosen && onScanner(picker.chosen)} className="justify-self-start">
          <ScanIcon size={18} aria-hidden /> Start scanning
        </Button>
      </div>
      <div className="grid content-start gap-3">
        <Field label="Or watch the folder your scanner saves into" hint="New pages are picked up within a few seconds.">
          <TextInput value={folder} placeholder="C:\Users\you\Scans" onChange={(e) => setFolder(e.target.value)} />
        </Field>
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy || !folder.trim()} onClick={onWatch}><FolderOpenIcon size={18} aria-hidden /> Watch folder</Button>
          <label className={`inline-flex cursor-pointer items-center gap-2 rounded-lg border border-control px-4 py-2 text-sm font-medium hover:bg-bg ${busy ? 'pointer-events-none opacity-40' : ''}`}>
            <UploadSimpleIcon size={18} aria-hidden /> Upload files
            <input type="file" multiple accept="image/*,.pdf" className="sr-only" aria-label="Upload scanned pages"
              onChange={(e) => { const fs = [...(e.target.files ?? [])]; e.target.value = ''; if (fs.length) onUpload(fs) }} />
          </label>
        </div>
      </div>
    </Surface>
  )
}
