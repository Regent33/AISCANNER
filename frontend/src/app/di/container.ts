import { HttpClient } from '@shared/infrastructure/http/httpClient'
import { consoleLogger } from '@shared/infrastructure/logger/logger'
import { LocalStore } from '@shared/infrastructure/storage/localStore'
import { API_BASE, STORE_NAMESPACE } from '@app/config/constants'

/** Global container, built eagerly at boot. Feature modules (features/x/di) build on top of it lazily. */
export const container = Object.freeze({
  logger: consoleLogger,
  http: new HttpClient(API_BASE, consoleLogger),
  store: new LocalStore(STORE_NAMESPACE),
})

export type Container = typeof container
