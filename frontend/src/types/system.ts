export type ComponentStatus = 'PASS' | 'FAIL' | 'SKIPPED' | 'UNAVAILABLE'
export type JobRunStatus = 'PENDING' | 'RUNNING' | 'PASS' | 'FAIL' | 'SKIPPED'

export interface ComponentHealth {
  status: ComponentStatus
  detail: string
}

export interface HealthResponse {
  status: 'PASS' | 'DEGRADED' | 'FAIL'
  database: ComponentHealth
  x_api: ComponentHealth
  telegram_api: ComponentHealth
  scheduler: ComponentHealth
  analytics: ComponentHealth
  event_count: number
  real_event_count: number
  replay_event_count: number
  updated_at: string
  platforms: PlatformDataSummary[]
}

export interface PlatformDataSummary {
  platform: string
  event_count: number
  real_event_count: number
  replay_event_count: number
  latest_created_at: string | null
  latest_collected_at: string | null
}

export interface JobStatus {
  name: string
  interval_seconds: number
  status: JobRunStatus
  last_started_at: string | null
  last_finished_at: string | null
  next_run_at: string | null
  processed_count: number
  total_processed_count: number
  duration_ms: number | null
  error: string | null
  detail: string | null
  run_count: number
  overlap_skips: number
}

export interface SchedulerStatus {
  enabled: boolean
  running: boolean
  started_at: string | null
  stopped_at: string | null
  jobs: JobStatus[]
}
