export type AnalysisStatus = 'PASS' | 'FAIL' | 'SKIPPED' | 'INSUFFICIENT_DATA'

export interface TemporalPoint {
  window_start: string
  window_end: string
  event_count: number
  positive_ratio: number
  neutral_ratio: number
  negative_ratio: number
  emotion_distribution: Record<string, number>
  anxiety_average: number
  excitement_average: number
  irony_rate: number
  stance_distribution: Record<string, number>
}

export interface TemporalSeriesResponse {
  rolling_1h: TemporalPoint[]
  daily: TemporalPoint[]
}

export interface TopicSummary {
  topic_id: number | null
  topic: string
  keywords: string[]
  volume: number
  growth: number | null
  velocity: number | null
  acceleration: number | null
  window_start: string | null
  window_end: string | null
  status: string
  sentiment: Record<string, number>
  source: string
}

export interface TopicEvolutionPoint {
  window_start: string
  window_end: string
  volume: number
  growth: number | null
  velocity: number | null
  acceleration: number | null
  status: string
  sentiment: Record<string, number>
}

export interface TopicDetail extends TopicSummary {
  model_name: string | null
  first_seen_at: string | null
  last_seen_at: string | null
  evolution: TopicEvolutionPoint[]
}

export interface TrendAnalyticsResponse {
  status: AnalysisStatus
  temporal_status: AnalysisStatus
  engine: string
  fallback: boolean
  items: TopicSummary[]
  detail: string | null
}

export interface TopicListResponse {
  status: AnalysisStatus
  engine: string
  items: TopicSummary[]
  detail: string | null
}

export interface TopicEvolutionResponse {
  status: AnalysisStatus
  topic_id: number
  topic: string
  items: TopicEvolutionPoint[]
  detail: string | null
}


export type DimensionStatus = 'AVAILABLE' | 'INSUFFICIENT_DATA' | 'UNAVAILABLE' | 'ERROR'

export interface AggregateSegment {
  label: string
  count: number
  share: number
  avg_confidence: number | null
}

export interface DimensionDistribution {
  dimension: 'age' | 'geography' | 'language' | 'profession'
  status: DimensionStatus
  detail: string
  total_subjects: number
  unknown_count: number
  segments: AggregateSegment[]
  updated_at: string | null
}

export interface DemographicsResponse {
  status: DimensionStatus
  detail: string
  total_subjects: number
  dimensions: Record<string, DimensionDistribution>
  updated_at: string | null
}
