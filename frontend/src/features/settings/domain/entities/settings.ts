export type Provider = 'local' | 'cloud' | 'openrouter' | 'nvidia'

export type Settings = {
  provider: Provider
  threshold: number
  cloudModel: string
  openrouterModel: string
  nvidiaModel: string
  keyCounts: Record<'openrouter' | 'nvidia', number>
  savedModels: Record<'openrouter' | 'nvidia', string[]>
  newKeys: string
  watchFolder: string
  showNames: boolean
}
