import type { TemporalPoint } from '../types/analytics'
import type { CanonicalEvent, EnrichedEvent } from '../types/events'

export interface HeatmapCell {
  day: number
  hourBucket: number
  count: number
  intensity: number
}

export function buildHeatmap(events: CanonicalEvent[]): HeatmapCell[] {
  const counts = new Map<string, number>()
  events.forEach((event) => {
    const date = new Date(event.created_at)
    const day = (date.getUTCDay() + 6) % 7
    const hourBucket = Math.floor(date.getUTCHours() / 3)
    const key = `${day}-${hourBucket}`
    counts.set(key, (counts.get(key) ?? 0) + 1)
  })
  const max = Math.max(1, ...counts.values())
  return Array.from({ length: 7 * 8 }, (_, index) => {
    const day = Math.floor(index / 8)
    const hourBucket = index % 8
    const count = counts.get(`${day}-${hourBucket}`) ?? 0
    return { day, hourBucket, count, intensity: count / max }
  })
}

export function emotionTotals(points: TemporalPoint[]): Record<string, number> {
  const latest = points.at(-1)
  if (!latest) return {}
  return Object.fromEntries(
    Object.entries(latest.emotion_distribution)
      .filter(([label]) => label !== 'nervousness')
      .sort(([, left], [, right]) => right - left)
      .slice(0, 8),
  )
}

export function activeUsers(events: CanonicalEvent[]): number {
  return new Set(events.map((event) => `${event.platform}:${event.author.platform_user_id}`)).size
}

export function sentimentShift(points: TemporalPoint[]): number | null {
  if (points.length < 2) return null
  return points.at(-1)!.positive_ratio - points.at(-2)!.positive_ratio
}

export function filterTemporalRange(points: TemporalPoint[], range: '1H' | '6H' | '24H' | '7D') {
  if (!points.length) return []
  const hours = { '1H': 1, '6H': 6, '24H': 24, '7D': 24 * 7 }[range]
  const end = new Date(points.at(-1)!.window_end).getTime()
  return points.filter((point) => new Date(point.window_end).getTime() >= end - hours * 3_600_000)
}

export interface EventFilters {
  search: string
  platform: string
  sentiment: string
  emotion: string
  interaction: string
}

export function filterEnrichedEvents(items: EnrichedEvent[], filters: EventFilters) {
  const search = filters.search.trim().toLowerCase()
  return items.filter(({ event, analysis }) => {
    const matchesSearch =
      !search ||
      event.content.text.toLowerCase().includes(search) ||
      event.author.username?.toLowerCase().includes(search) ||
      event.content.hashtags.some((tag) => tag.toLowerCase().includes(search))
    return (
      matchesSearch &&
      (filters.platform === 'all' || event.platform === filters.platform) &&
      (filters.sentiment === 'all' || analysis?.sentiment.label === filters.sentiment) &&
      (filters.emotion === 'all' || analysis?.emotions.primary_label === filters.emotion) &&
      (filters.interaction === 'all' || event.interaction_type === filters.interaction)
    )
  })
}
