import { useQuery } from '@tanstack/react-query'
import { container } from '@app/di/container'
import { HEALTH_POLL_MS } from '@app/config/constants'
import { unwrap } from '@shared/kernel/types/result'

export function useHealth() {
  const q = useQuery({
    queryKey: ['health'],
    queryFn: async () => unwrap(await container.http.get<{ ok: boolean }>('/health')),
    refetchInterval: HEALTH_POLL_MS,
  })
  return q.isSuccess ? 'Server connected' : q.isError ? 'Server not reachable' : 'Connecting'
}
