export type Platform = 'x' | 'telegram' | 'youtube' | 'instagram' | 'facebook' | 'reddit'

export interface AuthorInfo {
  platform_user_id: string
  username: string | null
  display_name: string | null
  bio: string | null
  location_raw: string | null
  avatar_url: string | null
  followers_count: number
  following_count: number
  is_verified: boolean | null
}

export interface MediaInfo {
  media_key: string | null
  media_type: string
  url: string | null
  preview_url: string | null
  alt_text: string | null
}

export interface CanonicalEvent {
  event_id: string
  platform: Platform
  platform_post_id: string
  parent_platform_post_id: string | null
  thread_root_id: string | null
  interaction_type: string
  created_at: string
  collected_at: string
  author: AuthorInfo
  content: {
    text: string
    language: string | null
    hashtags: string[]
    mentions: string[]
    media: MediaInfo[]
  }
  relationships: Record<string, string | null>
  metrics: {
    likes: number
    shares: number
    comments: number
    views: number
    quotes: number
    bookmarks: number
  }
  source_metadata: Record<string, unknown>
}

export interface ClassificationResult {
  label: string
  confidence: number
  scores: Record<string, number>
  model_name: string
  model_version: string
}

export interface NLPResult {
  sentiment: ClassificationResult
  emotions: {
    primary_label: string | null
    scores: Record<string, number>
    native_scores: Record<string, number>
    model_name: string
    model_version: string
  }
  irony: {
    is_ironic: boolean
    confidence: number
    scores: Record<string, number>
    model_name: string
    model_version: string
  }
  stance: {
    target: string | null
    label: string | null
    confidence: number | null
    scores: Record<string, number>
    supported: boolean
    reason: string | null
    model_name: string | null
    model_version: string | null
  }
  processed_at: string
}

export interface EnrichedEvent {
  event: CanonicalEvent
  analysis: NLPResult | null
}

export interface EventListResponse {
  items: CanonicalEvent[]
  count: number
  total: number
  offset: number
  limit: number
}

export interface EnrichedEventListResponse {
  items: EnrichedEvent[]
  count: number
  total: number
  offset: number
  limit: number
}

export interface LiveEventsResponse {
  mode: 'live' | 'replay' | 'mixed' | 'idle'
  label: string
  items: CanonicalEvent[]
}

