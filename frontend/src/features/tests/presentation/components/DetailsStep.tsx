import { Field, TextInput } from '@shared/ui'
import type { Details } from '../viewmodels/useNewTestViewModel'

export function DetailsStep({ value, onChange }: { value: Details; onChange: (d: Details) => void }) {
  return (
    <div className="grid gap-4 md:max-w-md">
      <Field label="Test name">
        <TextInput value={value.name} autoFocus onChange={(e) => onChange({ ...value, name: e.target.value })} />
      </Field>
      <Field label="Subject">
        <TextInput value={value.subject} onChange={(e) => onChange({ ...value, subject: e.target.value })} />
      </Field>
      <Field label="Pages per paper" hint="Optional. Used to spot missing or extra pages.">
        <TextInput type="number" min={1} inputMode="numeric" className="w-32" value={value.pages}
          onChange={(e) => onChange({ ...value, pages: e.target.value })} />
      </Field>
    </div>
  )
}
