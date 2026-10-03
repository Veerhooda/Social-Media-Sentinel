import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { health, stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { LiveFeedPage } from './LiveFeedPage'

afterEach(() => vi.unstubAllGlobals())

const ID = '7f6c1c1e-0000-4000-8000-000000000001'
const enriched = {
  event: {
    event_id: ID, platform: 'telegram', platform_post_id: '461', parent_platform_post_id: null, thread_root_id: null, interaction_type: 'post',
    created_at: '2026-10-03T10:00:00Z', collected_at: '2026-10-03T10:01:00Z',
    author: { platform_user_id: 'c1', username: 'durov', display_name: 'Pavel', followers_count: null, following_count: null, verified: null, profile_metadata: {} },
    content: { text: 'An older channel post', language: 'en', hashtags: [], mentions: [], media: [] },
    relationships: {}, metrics: { likes: 1, shares: 2, comments: 3, views: 400, quotes: 0, bookmarks: 0 }, source_metadata: { channel_username: 'durov', message_id: '461', replay: false },
  },
  analysis: null,
}

it('opens a deep-linked event even when it is not on the current page', async () => {
  const calls = stubApi([
    ['/health', health()],
    [`/events/${ID}/enriched`, enriched],
    ['/events/enriched', { items: [], count: 0, total: 0, offset: 0, limit: 25 }],
    ['/analytics/emotions', { rolling_1h: [], daily: [] }],
  ])
  renderPage(<Routes><Route path="/live-feed" element={<LiveFeedPage />} /></Routes>, `/live-feed?event=${ID}`)
  const drawer = await screen.findByRole('dialog', { name: 'Event details' })
  expect(within(drawer).getByText('An older channel post')).toBeInTheDocument()
  expect(within(drawer).getByText('Waiting for the NLP job.')).toBeInTheDocument()
  expect(within(drawer).getByRole('link', { name: /Open on Telegram/ })).toHaveAttribute('href', 'https://t.me/durov/461')
  expect(calls.some((call) => call.url.includes(`/events/${ID}/enriched`))).toBe(true)
})
