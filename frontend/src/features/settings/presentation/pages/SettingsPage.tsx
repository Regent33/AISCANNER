import { Banner, Button, Field, Page, Select, Skeleton, Surface, TextInput } from '@shared/ui'
import { pct } from '@shared/utils/format'
import { ProviderChoice } from '../components/ProviderChoice'
import { THRESHOLD_RANGE } from '../../domain/usecases/SaveSettings'
import { useSettingsViewModel } from '../viewmodels/useSettingsViewModel'

export default function SettingsPage() {
  const vm = useSettingsViewModel()
  const f = vm.form
  const hosted = f?.provider === 'nvidia' || f?.provider === 'openrouter' ? f.provider : null
  const name = hosted === 'nvidia' ? 'NVIDIA NIM' : 'OpenRouter'
  const modelField = hosted === 'nvidia' ? 'nvidiaModel' : 'openrouterModel'
  return (
    <Page title="Settings" action={<Button variant="primary" disabled={!vm.dirty || vm.saving} onClick={vm.save}>Save</Button>}>
      {vm.error && <Banner tone="danger">{vm.error}</Banner>}
      {vm.saved && <Banner tone="info">Saved.</Banner>}
      {vm.loading || !f ? <Skeleton className="h-64" /> : (
        <Surface className="grid gap-8">
          <ProviderChoice value={f.provider} onChange={(provider) => vm.update({ provider, newKeys: '' })} />
          {hosted && (
            <div className="grid gap-2 md:max-w-lg">
              <Field label="Saved models">
                <Select value={f.savedModels[hosted].includes(f[modelField]) ? f[modelField] : ''}
                  options={[...f.savedModels[hosted].map((model) => ({ label: model, value: model })), { label: 'Enter a new model ID', value: '' }]}
                  onChange={(e) => vm.update({ [modelField]: e.target.value })} />
              </Field>
              <Field label={`${name} model ID`} hint="Enter a model ID and save settings to use it and add it to this provider’s list. For handwriting, choose a model that accepts images.">
                <TextInput value={f[modelField]} maxLength={256} spellCheck={false} autoCapitalize="none"
                  onChange={(e) => vm.update({ [modelField]: e.target.value })} />
              </Field>
              <a href={hosted === 'nvidia' ? 'https://build.nvidia.com/models' : 'https://openrouter.ai/models'}
                target="_blank" rel="noreferrer" className="justify-self-start text-sm text-accent underline">
                Browse {name} models
              </a>
              <Field label="Add API keys" hint={`${f.keyCounts[hosted]} configured. Separate new keys with commas. Keys added here last until the server restarts.`}>
                <TextInput type="password" value={f.newKeys} autoComplete="off" spellCheck={false}
                  onChange={(e) => vm.update({ newKeys: e.target.value })} />
              </Field>
              <div className="justify-self-start">
                <Button variant="primary" disabled={!vm.dirty || vm.saving} onClick={vm.save}>Save settings</Button>
              </div>
            </div>
          )}
          {f.provider !== 'local' && <p className="text-sm text-muted">The provider receives redacted answer crops,
            question and syllabus text, and topic-level results for reports.</p>}
          <Field label={`Ask me to check an answer when the AI is less than ${pct(f.threshold)} sure`}
            hint="Higher means more answers to check by hand, and fewer AI mistakes.">
            <input type="range" min={THRESHOLD_RANGE[0]} max={THRESHOLD_RANGE[1]} step={0.01} value={f.threshold}
              onChange={(e) => vm.update({ threshold: Number(e.target.value) })} className="w-full max-w-md accent-[var(--accent)]" />
          </Field>
          <div className="md:max-w-lg">
            <Field label="Scanner folder" hint="The folder your scanner software saves into. Used by Watch folder.">
              <TextInput value={f.watchFolder} onChange={(e) => vm.update({ watchFolder: e.target.value })} />
            </Field>
          </div>
          <label className="flex items-start gap-3">
            <input type="checkbox" checked={f.showNames} onChange={(e) => vm.update({ showNames: e.target.checked })}
              className="mt-1 accent-[var(--accent)]" />
            <span>
              <span className="font-medium">Show student names on this computer</span>
              <span className="block text-sm text-muted">Names are read and kept on this computer only. They are never sent to the cloud.</span>
            </span>
          </label>
        </Surface>
      )}
    </Page>
  )
}
