import { Link } from 'react-router-dom'
import { ROUTES } from '@app/config/constants'
import { Banner, EmptyState, Field, Page, Select, Skeleton } from '@shared/ui'
import type { TestId } from '@shared/kernel/types/ids'
import { BatchHistory } from '../components/BatchHistory'
import { BatchProgress } from '../components/BatchProgress'
import { ScanSources } from '../components/ScanSources'
import { useScanViewModel } from '../viewmodels/useScanViewModel'

export default function ScanPage() {
  const vm = useScanViewModel()
  if (vm.testsLoading) return <Page title="Scan"><Skeleton className="h-40" /></Page>
  if (vm.tests.length === 0) {
    return (
      <Page title="Scan">
        <EmptyState title="Create a test first">
          The scanner needs the answer key. <Link className="text-accent underline" to={ROUTES.newTest}>Create a test</Link>.
        </EmptyState>
      </Page>
    )
  }
  return (
    <Page title="Scan">
      <div className="md:max-w-md">
        <Field label="Test">
          <Select value={vm.testId ?? ''} onChange={(e) => vm.setTestId(Number(e.target.value) as TestId)}
            options={vm.tests.map((t) => ({ value: t.id, label: t.name }))} />
        </Field>
      </div>
      {vm.error && <Banner tone="danger">{vm.error}</Banner>}
      {vm.notice && <Banner tone="info">{vm.notice}</Banner>}
      <ScanSources folder={vm.folder} setFolder={vm.setFolder} busy={vm.busy}
        onScanner={vm.startScanner} onWatch={vm.watchFolder} onUpload={vm.upload} />
      <BatchHistory batches={vm.batches} current={vm.batch?.id ?? null} onPick={vm.chooseBatch} onNew={vm.newBatch} />
      {vm.batch
        ? <BatchProgress batch={vm.batch} onPauseResume={vm.pauseOrResume} onFinish={vm.finish} />
        : <EmptyState title="No pages yet">Start the scanner, watch a folder, or upload scans to begin.</EmptyState>}
    </Page>
  )
}
