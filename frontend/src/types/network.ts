export interface NodeMetrics {
  node_id: string
  in_degree_centrality: number
  out_degree_centrality: number
  betweenness_centrality: number
  closeness_centrality: number
  pagerank: number
  hub_score: number
  authority_score: number
  community: number | null
}

export interface NetworkSummary {
  nodes: number
  edges: number
  density: number
  communities: number
  metrics: NodeMetrics[]
  interpretation: string
}

export interface NetworkResponse {
  summary: NetworkSummary
}

export interface NetworkGraphEdge {
  event_id: string
  source: string
  target: string
  interaction_type: string
  weight: number
  occurred_at: string
}

export interface NetworkGraphResponse {
  nodes: NodeMetrics[]
  edges: NetworkGraphEdge[]
  node_count: number
  edge_count: number
}


export interface TemporalSnapshot {
  window_start: string
  window_end: string
  label: string
  nodes: number
  edges: number
  density: number
  communities: number
}

export interface InfluenceDelta {
  node_id: string
  metric: string
  first_value: number
  last_value: number
  change: number
  direction: string
  windows_measured: number
}

export interface TemporalNetworkResponse {
  window: string
  window_count: number
  anchored_at: string | null
  snapshots: TemporalSnapshot[]
  influence_changes: InfluenceDelta[]
  detail: string
}

export interface InfluenceEntry extends NodeMetrics {
  node_id: string
}

export interface InfluenceResponse {
  metric: string
  window_start: string | null
  window_end: string | null
  nodes: number
  edges: number
  items: InfluenceEntry[]
  detail: string
}

export interface CommunityProfile {
  community_id: number
  size: number
  interaction_volume: number
  dominant_interaction_types: string[]
  interaction_type_counts: Record<string, number>
  first_seen_at: string | null
  last_seen_at: string | null
}

export interface CommunityListResponse {
  window_start: string | null
  window_end: string | null
  communities: CommunityProfile[]
  detail: string
}

export interface CascadeSummary {
  cascade_id: string
  platform: string
  root_platform_post_id: string
  event_count: number
  depth: number
  width: number
  duration_seconds: number | null
  participant_count: number
  community_count: number
  interaction_types: string[]
  started_at: string | null
  last_activity_at: string | null
  provenance: string
}

export interface PropagationStep {
  depth: number
  node_id: string
  event_id: string
  platform_post_id: string
  interaction_type: string
  occurred_at: string
  community: number | null
  sentiment: string | null
  emotion: string | null
  is_ironic: boolean | null
}

export interface CascadeDetail extends CascadeSummary {
  communities: number[]
  sentiment_composition: Record<string, number>
  sentiment_counts: Record<string, number>
  propagation_path: PropagationStep[]
}

export interface CascadeListResponse {
  cascades: CascadeSummary[]
  count: number
  largest_cascade_id: string | null
  max_depth: number
  detail: string
}
