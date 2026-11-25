import { useParams } from 'react-router-dom'
import { Banner, Button, Page, Surface } from '@shared/ui'
import { asId, type TestId } from '@shared/kernel/types/ids'
import { DetailsStep } from '../components/DetailsStep'
import { PrintStep } from '../components/PrintStep'
import { TextOrFileInput } from '../components/TextOrFileInput'
import { WizardSteps } from '../components/WizardSteps'
import { STEPS, useNewTestViewModel } from '../viewmodels/useNewTestViewModel'

const KEY_EXAMPLE = '1. B\n2. photosynthesis\n3. Mercury; Venus\n\nor, with question text:\n4 | mcq | C | 1 | Which ocean did Columbus cross?'
const KEY_HELP = 'One line per question. No answers? Leave them out ("4 | mcq | | 1 | question text") and the AI will suggest them.'
const SYL_EXAMPLE = 'PLANT | Plant life | photosynthesis, roots, leaves\nForces and motion: friction, gravity, speed'

export default function NewTestPage() {
  const { id } = useParams()
  const vm = useNewTestViewModel(id ? asId<TestId>(Number(id)) : null)
  return (
    <Page title={vm.editing ? 'Edit test' : 'New test'}>
      <WizardSteps steps={STEPS} current={vm.step} />
      <Surface className="grid gap-6">
        {vm.step === 0 && <DetailsStep value={vm.details} onChange={vm.setDetails} />}
        {vm.step === 1 && <TextOrFileInput label="Answer key" example={KEY_EXAMPLE} help={KEY_HELP} value={vm.key} onChange={vm.setKey} />}
        {vm.step === 2 && (
          <TextOrFileInput label="Syllabus" example={SYL_EXAMPLE} help="One topic per line." value={vm.syllabus} onChange={vm.setSyllabus} />
        )}
        {vm.step === 3 && <PrintStep printUrl={vm.printUrl} printed={vm.printed} onPrinted={vm.markPrinted}
          sampleUrl={vm.sampleUrl} box={vm.box} onBox={vm.setBox} onSample={vm.uploadSample} />}
        {vm.editing && <p className="text-sm text-muted">Leave a step empty to keep what the test already has.</p>}
        {vm.notice && <Banner tone="info">{vm.notice}</Banner>}
        {vm.error && <Banner tone="danger">{vm.error}</Banner>}
        <div className="flex justify-between gap-3">
          {vm.canGoBack ? <Button variant="quiet" onClick={vm.back}>Back</Button> : <span />}
          <Button variant="primary" disabled={!vm.canAdvance} onClick={vm.next}>
            {vm.isLast ? (vm.editing ? 'Save' : 'Save and start scanning') : 'Continue'}
          </Button>
        </div>
      </Surface>
    </Page>
  )
}
