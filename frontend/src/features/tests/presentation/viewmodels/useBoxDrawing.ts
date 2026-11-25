import { useRef, type KeyboardEvent, type PointerEvent } from 'react'
import type { Box } from '../../domain/entities/test'

const START: Box = [0.08, 0.05, 0.91, 0.16]  // typical name/ID/year/section block at the top of page 1
const STEP = 0.01
const clamp = (v: number) => Math.min(1, Math.max(0, v))

/** Draw a rectangle by dragging, or with the keyboard: Enter places one, arrows move it, Shift+arrows resize. */
export function useBoxDrawing(box: Box | null, onChange: (b: Box) => void) {
  const start = useRef<[number, number] | null>(null)

  const at = (e: PointerEvent<HTMLElement>): [number, number] => {
    const r = e.currentTarget.getBoundingClientRect()
    return [clamp((e.clientX - r.left) / r.width), clamp((e.clientY - r.top) / r.height)]
  }
  const draw = (a: [number, number], b: [number, number]) =>
    onChange([Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])])

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    const d = { ArrowLeft: [-STEP, 0], ArrowRight: [STEP, 0], ArrowUp: [0, -STEP], ArrowDown: [0, STEP] }[e.key]
    if (e.key === 'Enter' && !box) onChange(START)
    else if (d && box) {
      const [x0, y0, x1, y1] = box
      onChange(e.shiftKey
        ? [x0, y0, clamp(Math.max(x0 + STEP, x1 + d[0])), clamp(Math.max(y0 + STEP, y1 + d[1]))]
        : [clamp(x0 + d[0]), clamp(y0 + d[1]), clamp(x1 + d[0]), clamp(y1 + d[1])])
    } else return
    e.preventDefault()
  }

  return {
    onKeyDown,
    onPointerDown: (e: PointerEvent<HTMLElement>) => {
      e.currentTarget.setPointerCapture(e.pointerId)
      start.current = at(e)
      draw(start.current, start.current)
    },
    onPointerMove: (e: PointerEvent<HTMLElement>) => { if (start.current) draw(start.current, at(e)) },
    onPointerUp: () => { start.current = null },
  }
}
