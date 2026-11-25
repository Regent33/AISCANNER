import { PrinterIcon } from '@phosphor-icons/react'
import type { Box } from '../../domain/entities/test'
import { IdentityAreaStep } from './IdentityAreaStep'

type Props = {
  printUrl: string | null; printed: boolean; onPrinted: () => void
  sampleUrl: string | null; box: Box | null; onBox: (b: Box) => void; onSample: (f: File) => void
}

const PRIMARY = 'inline-flex items-center gap-2 justify-self-start rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90'

/** Teachers print the test from the app, so every paper carries what the scanner needs to read it. */
export function PrintStep({ printUrl, printed, onPrinted, ...area }: Props) {
  return (
    <div className="grid gap-5">
      <p className="max-w-[65ch] text-muted">
        Print the test from here and hand it out. Each page carries corner marks and a page number so the scanner can
        read it, and page 1 has boxes for name, ID, year and section. That area is read on this computer only and blacked
        out before anything else looks at the page.
      </p>
      {printUrl && (
        <a className={PRIMARY} href={printUrl} download onClick={onPrinted}>
          <PrinterIcon size={18} aria-hidden /> Download printable test
        </a>
      )}
      {printed && <p className="text-sm text-muted" role="status">Downloaded. Open the PDF and print it on A4 paper, one side only.</p>}
      <details className="text-sm">
        <summary className="cursor-pointer text-muted">Adjust the student details area</summary>
        <div className="mt-4"><IdentityAreaStep {...area} /></div>
      </details>
    </div>
  )
}
