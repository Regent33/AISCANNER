import { useState } from 'react'
import { Button, Field, Surface, TextInput } from '@shared/ui'
import type { IdentityFix, IdentityItem } from '../../domain/entities/reviewItem'

type Props = { item: IdentityItem; onSave: (fix: IdentityFix) => void }

/** Shows the unredacted name area (ID, year, section). It stays on this computer. */
export function IdentityReview({ item, onSave }: Props) {
  const [fix, setFix] = useState<IdentityFix>({ studentId: item.readId ?? '', year: item.year ?? '', section: item.section ?? '' })
  const set = (k: keyof IdentityFix) => (e: React.ChangeEvent<HTMLInputElement>) => setFix({ ...fix, [k]: e.target.value })
  return (
    <Surface className="grid gap-5">
      <div>
        <h2 className="text-lg font-medium">Student details</h2>
        <p className="text-sm text-warn">{item.problem}</p>
      </div>
      <img src={item.imageUrl} alt="Name, ID, year and section area of page 1" className="w-full rounded-lg border border-line bg-white" />
      <form className="grid gap-4 sm:grid-cols-[14rem_6rem_12rem_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); onSave(fix) }}>
        <Field label="Student ID"><TextInput value={fix.studentId} autoFocus onChange={set('studentId')} /></Field>
        <Field label="Year"><TextInput value={fix.year} inputMode="numeric" onChange={set('year')} /></Field>
        <Field label="Section"><TextInput value={fix.section} onChange={set('section')} /></Field>
        <Button type="submit" variant="primary" disabled={!fix.studentId.trim()}>Save</Button>
      </form>
    </Surface>
  )
}
