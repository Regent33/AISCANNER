import { useSearchParams } from 'react-router-dom'

type Memory = { get<T>(key: string, fallback: T): T; set(key: string, value: unknown): void }

/** Selected id from ?param=, else the remembered one, else the first option. Setting it updates both. */
export function useUrlSelection<T extends number>(param: string, options: { id: T }[], memory: Memory, memoryKey: string) {
  const [params, setParams] = useSearchParams()
  const ids = new Set(options.map((o) => o.id as number))
  const fromUrl = Number(params.get(param))
  const remembered = memory.get<number | null>(memoryKey, null)
  const value = (ids.has(fromUrl) ? fromUrl : remembered !== null && ids.has(remembered) ? remembered : options[0]?.id ?? null) as T | null
  const set = (id: T) => {
    memory.set(memoryKey, id)
    setParams((p) => { p.set(param, String(id)); return p }, { replace: true })
  }
  return [value, set] as const
}
