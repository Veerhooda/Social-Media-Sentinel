import { describe, expect, it } from 'vitest'
import type { TemporalPoint } from '../types/analytics'
import type { CanonicalEvent, EnrichedEvent } from '../types/events'
import { activeUsers, buildHeatmap, emotionTotals, filterEnrichedEvents, sentimentShift } from './dashboard'

const event = (id: string, createdAt: string, user = id): CanonicalEvent => ({
  event_id: id, platform: 'x', platform_post_id: id, parent_platform_post_id: null, thread_root_id: id,
  interaction_type: 'post', created_at: createdAt, collected_at: createdAt,
  author: { platform_user_id: user, username: user, display_name: null, bio: null, location_raw: null, avatar_url: null, followers_count: 0, following_count: 0, is_verified: false },
  content: { text: `Open research ${id}`, language: 'en', hashtags: ['AI'], mentions: [], media: [] },
  relationships: {}, metrics: { likes: 0, shares: 0, comments: 0, views: 0, quotes: 0, bookmarks: 0 }, source_metadata: { replay: false },
})

const point = (positive: number): TemporalPoint => ({
  window_start: '2026-09-20T10:00:00Z', window_end: '2026-09-20T11:00:00Z', event_count: 2,
  positive_ratio: positive, neutral_ratio: 0.3, negative_ratio: 0.2,
  emotion_distribution: { excitement: 0.6, nervousness: 0.2, anxiety: 0.2 }, anxiety_average: 0.2,
  excitement_average: 0.6, irony_rate: 0.1, stance_distribution: {},
})

describe('dashboard transformations', () => {
  it('builds a real UTC activity heatmap', () => {
    const timestamp = '2026-09-21T04:00:00Z'
    const expectedDay = (new Date(timestamp).getUTCDay() + 6) % 7
    const cells = buildHeatmap([event('one', timestamp)])
    expect(cells).toHaveLength(56)
    expect(cells.find((cell) => cell.day === expectedDay && cell.hourBucket === 1)?.count).toBe(1)
  })

  it('derives user and sentiment metrics from API data', () => {
    expect(activeUsers([event('one', '2026-09-20T10:00:00Z', 'same'), event('two', '2026-09-20T10:01:00Z', 'same')])).toBe(1)
    expect(sentimentShift([point(0.4), point(0.55)])).toBeCloseTo(0.15)
  })

  it('uses anxiety terminology without duplicating native nervousness', () => {
    expect(emotionTotals([point(0.5)])).toEqual({ excitement: 0.6, anxiety: 0.2 })
  })

  it('filters enriched events by persisted model labels', () => {
    const enriched: EnrichedEvent = {
      event: event('one', '2026-09-20T10:00:00Z'),
      analysis: {
        sentiment: { label: 'positive', confidence: 0.9, scores: {}, model_name: 'test', model_version: '1' },
        emotions: { primary_label: 'excitement', scores: {}, native_scores: {}, model_name: 'test', model_version: '1' },
        irony: { is_ironic: false, confidence: 0.1, scores: {}, model_name: 'test', model_version: '1' },
        stance: { target: null, label: null, confidence: null, scores: {}, supported: false, reason: 'unsupported', model_name: null, model_version: null },
        processed_at: '2026-09-20T10:01:00Z',
      },
    }
    expect(filterEnrichedEvents([enriched], { search: 'research', platform: 'x', sentiment: 'positive', emotion: 'excitement', interaction: 'post' })).toHaveLength(1)
    expect(filterEnrichedEvents([enriched], { search: '', platform: 'all', sentiment: 'negative', emotion: 'all', interaction: 'all' })).toHaveLength(0)
  })
})
