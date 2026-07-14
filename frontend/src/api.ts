import type { Character, Job, ProviderState, StudioContract } from './types'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'include',
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try {
      const data = await response.json() as { detail?: string }
      message = data.detail || message
    } catch { /* response is not JSON */ }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  contract: () => request<StudioContract>('/contract'),
  provider: () => request<ProviderState>('/provider/session'),
  connect: (apiKey: string, model: string) => request<ProviderState>('/provider/session', { method: 'PUT', body: JSON.stringify({ apiKey, model }) }),
  disconnect: () => request<ProviderState>('/provider/session', { method: 'DELETE' }),
  characters: () => request<{ items: Character[] }>('/characters'),
  character: (id: string) => request<Character>(`/characters/${id}`),
  createCharacter: (data: FormData) => request<Job>('/characters', { method: 'POST', body: data }),
  jobs: (characterId?: string) => request<{ items: Job[] }>(`/jobs${characterId ? `?characterId=${encodeURIComponent(characterId)}` : ''}`),
  job: (id: string) => request<Job>(`/jobs/${id}`),
  createAction: (characterId: string, payload: object) => request<Job>(`/characters/${characterId}/actions`, { method: 'POST', body: JSON.stringify(payload) }),
  review: (jobId: string, slot: string, decision: 'approved' | 'rejected', note = '') => request<Job>(`/jobs/${jobId}/outputs/${encodeURIComponent(slot)}/review`, { method: 'PUT', body: JSON.stringify({ decision, note }) }),
  select: (jobId: string, slot: string, versionId: string) => request<Job>(`/jobs/${jobId}/outputs/${encodeURIComponent(slot)}/selection`, { method: 'PUT', body: JSON.stringify({ versionId }) }),
  regenerate: (jobId: string, slot: string, note: string) => request<Job>(`/jobs/${jobId}/outputs/${encodeURIComponent(slot)}/regenerate`, { method: 'POST', body: JSON.stringify({ note }) }),
  promote: (jobId: string) => request<Job>(`/jobs/${jobId}/promote`, { method: 'POST', body: '{}' }),
  retry: (jobId: string) => request<Job>(`/jobs/${jobId}/retry`, { method: 'POST', body: '{}' }),
  cancel: (jobId: string) => request<Job>(`/jobs/${jobId}/cancel`, { method: 'POST', body: '{}' }),
}

