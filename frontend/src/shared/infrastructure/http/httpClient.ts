import { Failure, err, ok, type Result } from '@shared/kernel/types/result'
import type { Logger } from '@shared/infrastructure/logger/logger'

const OFFLINE = 'Cannot reach the scanner app. Check that it is running on this computer.'

/** fetch wrapper: JSON in, Result out. Never throws. */
export class HttpClient {
  private readonly base: string
  private readonly log: Logger
  constructor(base: string, log: Logger) {
    this.base = base
    this.log = log
  }

  url(path: string): string {
    return `${this.base}${path}`
  }

  get<T>(path: string, query?: Record<string, string | number | undefined>): Promise<Result<T>> {
    const qs = query
      ? '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
      : ''
    return this.send<T>(path + qs, { method: 'GET' })
  }

  post<T>(path: string, body?: unknown): Promise<Result<T>> {
    return this.send<T>(path, jsonInit('POST', body))
  }

  put<T>(path: string, body: unknown): Promise<Result<T>> {
    return this.send<T>(path, jsonInit('PUT', body))
  }

  patch<T>(path: string, body: unknown): Promise<Result<T>> {
    return this.send<T>(path, jsonInit('PATCH', body))
  }

  upload<T>(path: string, field: string, files: File[]): Promise<Result<T>> {
    const form = new FormData()
    for (const f of files) form.append(field, f)
    return this.send<T>(path, { method: 'POST', body: form })
  }

  private async send<T>(path: string, init: RequestInit): Promise<Result<T>> {
    let res: Response
    try {
      res = await fetch(this.url(path), init)
    } catch (e) {
      this.log.warn('http.offline', { path, error: String(e) })
      return err(new Failure(OFFLINE))
    }
    let body: unknown
    try {
      body = res.headers.get('content-type')?.includes('json') ? await res.json() : await res.text()
    } catch {
      body = null  // empty or malformed body: status decides
    }
    if (!res.ok) {
      const message = detail(body) || res.statusText || 'Request failed'
      this.log.warn('http.error', { path, status: res.status, message })
      return err(new Failure(message, res.status))
    }
    return ok(body as T)
  }
}

function jsonInit(method: string, body: unknown): RequestInit {
  return body === undefined ? { method } : { method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }
}

/** FastAPI errors look like {detail: "..."} or {detail: [{msg: "..."}]}. */
function detail(body: unknown): string {
  if (typeof body === 'string') return body.slice(0, 300)
  const d = (body as { detail?: unknown } | null)?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => (x as { msg?: string }).msg ?? '').filter(Boolean).join('; ')
  return ''
}
