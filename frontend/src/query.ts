import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { JobStatus } from './types'

const active = new Set<JobStatus>(['queued', 'planning', 'generating', 'processing', 'promoting'])

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.job(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && active.has(status) ? 1200 : false
    },
  })
}
