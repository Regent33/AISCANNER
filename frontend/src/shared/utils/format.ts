export const pct = (x: number | null | undefined): string => (x == null ? 'n/a' : `${Math.round(x * 100)}%`)

export function eta(seconds: number | null | undefined): string {
  if (seconds == null) return 'n/a'
  if (seconds < 60) return 'under a minute'
  const m = Math.round(seconds / 60)
  return m < 60 ? `about ${m} min` : `about ${Math.round(m / 6) / 10} h`
}

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`
