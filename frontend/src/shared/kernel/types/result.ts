/** A failed operation, carrying a message fit to show a teacher. */
export class Failure extends Error {
  readonly status: number | null
  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'Failure'
    this.status = status
  }
}

export type Result<T> = { ok: true; value: T } | { ok: false; error: Failure }

export const ok = <T>(value: T): Result<T> => ({ ok: true, value })
export const err = <T = never>(error: Failure): Result<T> => ({ ok: false, error })

export function map<A, B>(r: Result<A>, f: (a: A) => B): Result<B> {
  return r.ok ? ok(f(r.value)) : r
}

/** Bridge to TanStack Query, which expects thrown errors. */
export function unwrap<T>(r: Result<T>): T {
  if (r.ok) return r.value
  throw r.error
}
