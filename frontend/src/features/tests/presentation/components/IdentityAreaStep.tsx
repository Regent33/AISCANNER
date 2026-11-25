import { Field } from '@shared/ui'
import type { Box } from '../../domain/entities/test'
import { useBoxDrawing } from '../viewmodels/useBoxDrawing'

type Props = { sampleUrl: string | null; box: Box | null; onBox: (b: Box) => void; onSample: (f: File) => void }

export function IdentityAreaStep({ sampleUrl, box, onBox, onSample }: Props) {
  const drawing = useBoxDrawing(box, onBox)
  return (
    <div className="grid gap-4">
      <p className="max-w-[65ch] text-muted">
        Upload a clean scan of page 1, then drag one box over the place where students write their name, ID, year and section.
        That area is read on this computer only and blacked out before anything else looks at the page.
      </p>
      <Field label="Scan of page 1">
        <input type="file" accept="image/*" aria-label="Sample page"
          className="text-sm file:mr-3 file:rounded-lg file:border file:border-control file:bg-surface file:px-3 file:py-1.5"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onSample(f) }} />
      </Field>
      {sampleUrl && (
        <p id="identity-keys" className="text-sm text-muted">
          Drag on the page, or click it and press Enter to place a box, arrow keys to move it, Shift and arrows to resize.
        </p>
      )}
      {sampleUrl && (
        <div className="relative w-full max-w-[560px] cursor-crosshair touch-none select-none overflow-hidden rounded-lg border border-line"
          data-testid="identity-canvas" tabIndex={0} role="application" aria-describedby="identity-keys" {...drawing}>
          <img src={sampleUrl} alt="Page 1 of the test" draggable={false} className="pointer-events-none w-full" />
          {box && (
            <div aria-label="Student details area" className="absolute border-2 border-danger bg-danger/25" style={{
              left: `${box[0] * 100}%`, top: `${box[1] * 100}%`,
              width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%`,
            }} />
          )}
        </div>
      )}
    </div>
  )
}
