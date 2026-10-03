import { apiRequest } from './client'
import type { JobStatus } from '../types/system'

export type SourcePlatform = 'x' | 'telegram' | 'youtube'

export interface CollectionSource {
  source_id: string
  platform: SourcePlatform
  target: string
  label: string | null
  enabled: boolean
  last_run_at: string | null
  last_status: string | null
  last_detail: string | null
  last_fetched: number
  last_stored: number
  total_stored: number
  created_at: string | null
}

export interface PlatformCollector {
  platform: SourcePlatform
  credentials_configured: boolean
  credential_detail: string
  job_name: string
  interval_seconds: number
  sources: CollectionSource[]
}

export interface SourcesOverview {
  scheduler_enabled: boolean
  scheduler_running: boolean
  platforms: PlatformCollector[]
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const getSources = () => apiRequest<SourcesOverview>('/sources')
export const addSource = (platform: SourcePlatform, target: string, label?: string) =>
  apiRequest<CollectionSource>('/sources', json('POST', { platform, target, label: label || null }))
export const updateSource = (id: string, patch: { enabled?: boolean; label?: string }) =>
  apiRequest<CollectionSource>(`/sources/${id}`, json('PATCH', patch))
export const deleteSource = (id: string) => apiRequest<null>(`/sources/${id}`, { method: 'DELETE' })
export const runJob = (name: string) => apiRequest<JobStatus>(`/system/jobs/${encodeURIComponent(name)}/run`, json('POST'))
