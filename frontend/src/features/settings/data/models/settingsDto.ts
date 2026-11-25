export type SettingsDto = {
  provider: 'local' | 'cloud' | 'mock' | 'openrouter' | 'nvidia'
  confidence_threshold: number
  cloud_model: string
  openrouter_model: string
  nvidia_model: string
  key_counts: Record<'openrouter' | 'nvidia', number>
  saved_models?: Record<'openrouter' | 'nvidia', string[]>
  watch_folder: string | null
  show_names: number | boolean
}
