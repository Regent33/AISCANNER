import { useEffect } from 'react'
import type { ReviewItem } from '../../domain/entities/reviewItem'

type Handlers = { current: ReviewItem | null; next: () => void; prev: () => void; accept: () => void; score: (n: number) => void }

/** Enter accepts, a number key sets that score, J/K or arrows move. Ignored while typing in a field. */
export function useReviewKeys(h: Handlers) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement
      if (el.closest('input, textarea, select') || e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === 'ArrowDown' || e.key === 'j') h.next()
      else if (e.key === 'ArrowUp' || e.key === 'k') h.prev()
      else if (e.key === 'Enter' && h.current?.kind === 'answer') h.accept()
      else if (/^[0-9]$/.test(e.key) && h.current?.kind === 'answer') h.score(Number(e.key))
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [h])
}
