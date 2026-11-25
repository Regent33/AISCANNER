/** Namespaced JSON wrapper over localStorage. Holds UI preferences only, never student data. */
export class LocalStore {
  private readonly ns: string
  constructor(ns: string) {
    this.ns = ns
  }

  get<T>(key: string, fallback: T): T {
    try {
      const raw = localStorage.getItem(`${this.ns}:${key}`)
      return raw == null ? fallback : (JSON.parse(raw) as T)
    } catch {
      return fallback
    }
  }

  set(key: string, value: unknown): void {
    try {
      localStorage.setItem(`${this.ns}:${key}`, JSON.stringify(value))
    } catch {
      /* storage full or disabled: preferences are optional */
    }
  }
}
