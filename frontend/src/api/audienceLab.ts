import { apiRequest, queryString } from './client'

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export type JobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'CANCELLED'

export interface LabStatus {
  model_name: string
  api_configured: boolean
  base_url: string
  total_profiles: number
  by_source: Record<string, number>
  latest_segmentation_id: string | null
  platforms: string[]
}

export interface UpsertResult {
  created: number
  updated: number
  total_profiles: number
  by_source: Record<string, number>
}

export interface ProfileImportItem {
  source: string
  external_ref: string
  platform?: string | null
  label?: string | null
  attributes?: Record<string, unknown>
  behaviour?: Record<string, unknown>
  sample_texts?: string[]
  weight?: number
}

export interface AttributeBreakdown {
  [key: string]: { coverage_pct: number; top: { value: string; pct: number }[] }
}

export interface Persona {
  persona_name: string
  summary: string
  demographics: string
  interests: string[]
  values: string[]
  communication_style: string
  positive_triggers: string[]
  negative_triggers: string[]
  sarcasm_tendency: 'low' | 'medium' | 'high'
  evidence_strength: 'weak' | 'moderate' | 'strong'
  agent_instructions: string
  membership_rule?: string
}

export interface Segment {
  segment_id: string
  code: string
  name: string
  description: string
  defining_traits: string[]
  member_count: number
  weight_total: number
  share: number
  attribute_breakdown: AttributeBreakdown
  persona: Persona | null
}

export interface ProgressEvent {
  at: string
  level: 'info' | 'warn'
  message: string
}

export interface Progress {
  stage?: string
  done?: number
  total?: number
  step?: number | null
  steps?: number | null
  started_at?: string
  stage_started_at?: string
  last_activity_at?: string
  elapsed_seconds?: number
  calls?: { in_flight: number; finished: number; failed: number; retries: number }
  tokens?: { prompt: number; completion: number; reasoning: number }
  events?: ProgressEvent[]
  cancel_requested?: boolean
}

export interface Segmentation {
  segmentation_id: string
  status: JobStatus
  model_name: string
  params: Record<string, unknown>
  profile_count: number
  assigned_count: number
  rationale: string | null
  progress: Progress
  error: string | null
  created_at: string | null
  completed_at: string | null
  segments: Segment[]
}

export interface SegmentReaction {
  first_impression: string
  reaction_mix_pct: { positive: number; neutral: number; negative: number; sarcastic: number }
  interested_pct: number
  engage_pct: number
  share_pct: number
  interested_subgroups: { who: string; why: string; share_of_segment_pct: number }[]
  sample_reactions: { voice: string; tone: 'positive' | 'neutral' | 'negative' | 'sarcastic'; text: string }[]
  what_works: string[]
  what_fails: string[]
  misread_risks: string[]
  suggested_edits: { change: string; expected_effect: string }[]
  confidence: 'low' | 'medium' | 'high'
  confidence_reason: string
}

export interface PanelSegmentResult {
  segment_id: string
  code: string
  name: string
  share: number
  member_count: number
  status: 'PASS' | 'FAILED'
  reaction: SegmentReaction | null
  error: string | null
}

export interface WeightedMetrics {
  coverage_share: number
  positive?: number
  neutral?: number
  negative?: number
  sarcastic?: number
  interested?: number
  engage?: number
  share?: number
  net_sentiment?: number
}

export interface InterestedAudience {
  interested_share_of_audience_pct: number
  by_segment: { segment: string; code: string; pct_of_interested: number }[]
  attributes: Record<string, { value: string; pct: number }[]>
}

export interface PanelResult {
  segments: PanelSegmentResult[]
  weighted: WeightedMetrics
  interested_audience: InterestedAudience
}

export interface Analysis {
  headline: string
  verdict: 'post_as_is' | 'minor_edits' | 'major_rework' | 'do_not_post'
  summary: string
  key_insights: string[]
  risks: string[]
  interested_audience_profile: string
  recommendations: { change: string; rationale: string; segments_helped: string[]; segments_at_risk: string[]; priority: 'high' | 'medium' | 'low' }[]
  should_rewrite: boolean
  improved_post: string
  rewrite_notes: string
}

export interface Uplift {
  available: boolean
  reason?: string
  method?: string
  segments_compared?: number
  before?: WeightedMetrics
  after?: WeightedMetrics
  delta_pp?: Record<string, number>
  relative_pct?: Record<string, number | null>
  per_segment?: { code: string; name: string; share: number; interested_pp: number; engage_pp: number; negative_pp: number; sarcastic_pp: number }[]
}

export interface Simulation {
  simulation_id: string
  segmentation_id: string
  status: JobStatus
  model_name: string
  platform: string
  post_text: string
  media: { description?: string; mime?: string; sha256?: string }
  progress: Progress
  baseline: PanelResult | null
  analysis: Analysis | null
  improved_post: string | null
  improved: PanelResult | null
  uplift: Uplift | null
  error: string | null
  created_at: string | null
  completed_at: string | null
}

export interface SimulationSummary {
  simulation_id: string
  status: JobStatus
  platform: string
  post_text: string
  created_at: string | null
  headline: string | null
}

export interface SimulationInput {
  text: string
  platform: string
  segmentation_id?: string | null
  image_data_url?: string | null
  media_description?: string | null
  auto_improve: boolean
}

const base = '/audience-lab'

export const getLabStatus = () => apiRequest<LabStatus>(`${base}/status`)
export const syncProfiles = () => apiRequest<UpsertResult>(`${base}/profiles/sync`, json({}))
export const importProfiles = (profiles: ProfileImportItem[]) => apiRequest<UpsertResult>(`${base}/profiles/import`, json({ profiles }))
export const listSegmentations = (limit = 10) => apiRequest<Segmentation[]>(`${base}/segmentations${queryString({ limit })}`)
export const getSegmentation = (id: string) => apiRequest<Segmentation>(`${base}/segmentations/${id}`)
export const createSegmentation = (body: { focus?: string | null; min_segments?: number | null; max_segments?: number | null }) =>
  apiRequest<Segmentation>(`${base}/segmentations`, json(body))
export const createSimulation = (body: SimulationInput) => apiRequest<Simulation>(`${base}/simulations`, json(body))
export const getSimulation = (id: string) => apiRequest<Simulation>(`${base}/simulations/${id}`)
export const listSimulations = (limit = 12) => apiRequest<SimulationSummary[]>(`${base}/simulations${queryString({ limit })}`)

export const cancelSegmentation = (id: string) => apiRequest<Segmentation>(`${base}/segmentations/${id}/cancel`, json({}))
export const cancelSimulation = (id: string) => apiRequest<Simulation>(`${base}/simulations/${id}/cancel`, json({}))

export const isActive = (status: JobStatus | undefined) => status === 'QUEUED' || status === 'RUNNING'
