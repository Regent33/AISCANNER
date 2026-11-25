import type { Settings } from '../../domain/entities/settings'
import type { SettingsDto } from '../models/settingsDto'

export const toSettings = (d: SettingsDto): Settings => ({
  provider: d.provider === 'mock' ? 'local' : d.provider,
  threshold: d.confidence_threshold,
  cloudModel: d.cloud_model,
  openrouterModel: d.openrouter_model,
  nvidiaModel: d.nvidia_model,
  keyCounts: d.key_counts,
  savedModels: d.saved_models ?? { openrouter: [d.openrouter_model], nvidia: [d.nvidia_model] },
  newKeys: '',
  watchFolder: d.watch_folder ?? '',
  showNames: Boolean(d.show_names),
})

export const toSettingsDto = (s: Settings): Partial<SettingsDto> & { add_keys?: string } => ({
  provider: s.provider,
  confidence_threshold: s.threshold,
  cloud_model: s.cloudModel,
  ...(s.provider === 'openrouter' && { openrouter_model: s.openrouterModel.trim() }),
  ...(s.provider === 'nvidia' && { nvidia_model: s.nvidiaModel.trim() }),
  ...((s.provider === 'openrouter' || s.provider === 'nvidia') && s.newKeys && { add_keys: s.newKeys }),
  watch_folder: s.watchFolder || null,
  show_names: s.showNames,
})
