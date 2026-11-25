import { container } from '@app/di/container'
import { BatchRemoteDataSource } from '../data/datasources/remote/batchRemoteDataSource'
import { BatchRepositoryImpl } from '../data/repositories/batchRepositoryImpl'
import { ListScanTests } from '../domain/usecases/ListScanTests'
import { ListBatches } from '../domain/usecases/ListBatches'
import { GetBatchProgress } from '../domain/usecases/GetBatchProgress'
import { StartScanning } from '../domain/usecases/StartScanning'
import { UploadPages } from '../domain/usecases/UploadPages'
import { PauseOrResumeBatch } from '../domain/usecases/PauseOrResumeBatch'
import { FinishBatch } from '../domain/usecases/FinishBatch'
import { GetDefaultWatchFolder } from '../domain/usecases/GetDefaultWatchFolder'
import { FindScanners } from '../domain/usecases/FindScanners'
import { AddNetworkPrinter } from '../domain/usecases/AddNetworkPrinter'

function build() {
  const repo = new BatchRepositoryImpl(new BatchRemoteDataSource(container.http))
  return {
    listTests: new ListScanTests(repo),
    listBatches: new ListBatches(repo),
    getBatch: new GetBatchProgress(repo),
    startScanning: new StartScanning(repo),
    uploadPages: new UploadPages(repo),
    pauseOrResume: new PauseOrResumeBatch(repo),
    finishBatch: new FinishBatch(repo),
    defaultWatchFolder: new GetDefaultWatchFolder(repo),
    findScanners: new FindScanners(repo),
    addNetworkPrinter: new AddNetworkPrinter(repo),
    store: container.store,
  }
}

let mod: ReturnType<typeof build> | null = null
export const scanModule = () => (mod ??= build())
