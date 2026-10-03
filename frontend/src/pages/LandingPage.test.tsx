import { screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { health, stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { LandingPage } from './LandingPage'

afterEach(() => vi.unstubAllGlobals())

it('shows live numbers from the API and links into the app', async () => {
  stubApi([
    ['/health', health([{ platform: 'telegram', event_count: 10, real_event_count: 10, replay_event_count: 0, latest_created_at: null, latest_collected_at: new Date().toISOString() }])],
    ['/analytics/sentiment', { rolling_1h: [], daily: [] }],
  ])
  renderPage(<LandingPage />)
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Conversation analytics for X, Telegram and YouTube')
  expect(await screen.findByText('446')).toBeInTheDocument()
  expect(screen.getByText('Telegram')).toBeInTheDocument()
  expect(screen.getAllByRole('link', { name: /Open dashboard/ })[0]).toHaveAttribute('href', '/dashboard')
  expect(screen.getByRole('link', { name: 'Test a post' })).toHaveAttribute('href', '/audience-lab')
})

it('says so when the API is unreachable instead of showing placeholder data', async () => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))))
  renderPage(<LandingPage />)
  expect(await screen.findByText(/The API is not reachable/)).toBeInTheDocument()
})
