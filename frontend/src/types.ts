export type ViewId = 'side' | 'front' | 'three_quarter'
export type StyleId = 'hand_drawn' | 'anime' | 'semi_realistic'
export type JobStatus = 'queued' | 'planning' | 'generating' | 'processing' | 'awaiting_review' | 'promoting' | 'approved' | 'failed' | 'interrupted' | 'cancelled'

export interface StudioContract {
  version: string
  previewFps: number
  masterSize: number
  frameSize: number
  frameCounts: Array<8 | 12 | 16>
  views: Record<ViewId, { label: string; prompt: string }>
  styles: Record<StyleId, { label: string; prompt: string }>
  actions: Record<string, { label: string; loop: boolean; anchors: string[] }>
  jobStatuses: JobStatus[]
  imageModels: string[]
}

export interface ProviderState {
  configured: boolean
  verified: boolean
  model: string
  error?: string
  models: string[]
}

export interface Version {
  id: string
  label: string
  url: string
  width: number
  height: number
  quality: { warnings: string[]; coverage: number; footY: number }
  createdAt: string
}

export interface OutputSlot {
  slot: string
  label: string
  kind: 'master' | 'frame'
  index: number | null
  selectedVersionId: string
  review: { decision: 'pending' | 'approved' | 'rejected'; note: string }
  versions: Version[]
}

export interface Job {
  id: string
  type: 'character' | 'action'
  characterId: string
  status: JobStatus
  progress: number
  message: string
  error: string
  payload: Record<string, unknown> & {
    action?: string
    view?: ViewId
    frameCount?: 8 | 12 | 16
    loop?: boolean
    sequenceQuality?: { warnings: string[]; duplicatePairs: number[][] }
  }
  outputs: Record<string, OutputSlot>
  createdAt: string
  updatedAt: string
}

export interface Character {
  id: string
  name: string
  description: string
  style: StyleId
  customStyle: string
  status: 'draft' | 'approved'
  createdAt: string
  updatedAt: string
  masters: Partial<Record<ViewId, string>>
  actions: Array<{ jobId: string; action: string; view: ViewId; frameCount: number; loop: boolean }>
}
