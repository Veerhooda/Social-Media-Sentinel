import { screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { health, jobs, point, stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { OverviewPage } from './OverviewPage'

afterEach(() => vi.unstubAllGlobals())

const sources = {
  scheduler_enabled: true,
  scheduler_running: true,
  platforms: [
    { platform: 'x', credentials_configured: false, credential_detail: 'X_BEARER_TOKEN is not set in .env', job_name: 'x_recent_search', interval_seconds: 60, sources: [] },
    { platform: 'telegram', credentials_configured: true, credential_detail: 'ok', job_name: 'telegram_collection', interval_seconds: 120, sources: [{ source_id: '1', platform: 'telegram', target: 'durov', label: null, enabled: true, last_run_at: null, last_status: null, last_detail: null, last_fetched: 0, last_stored: 0, total_stored: 0, created_at: null }] },
    { platform: 'youtube', credentials_configured: true, credential_detail: 'ok', job_name: 'youtube_collection', interval_seconds: 60, sources: [] },
  ],
}

it('summarises stored data and shows each collector state from the API', async () => {
  stubApi([
    ['/health', health([
      { platform: 'x', event_count: 300, real_event_count: 296, replay_event_count: 4, latest_created_at: null, latest_collected_at: '2026-09-20T18:00:00Z' },
      { platform: 'telegram', event_count: 150, real_event_count: 150, replay_event_count: 0, latest_created_at: null, latest_collected_at: '2026-10-03T10:00:00Z' },
    ])],
    ['/system/jobs', jobs()],
    ['/sources', sources],
    ['/events', { items: [], count: 0, total: 0, offset: 0, limit: 1 }],
    ['/analytics/sentiment', { rolling_1h: [point('2026-10-03T09:00:00Z', 0.4, 0.2), point('2026-10-03T10:00:00Z', 0.5, 0.25)], daily: [] }],
    ['/analytics/emotions', { rolling_1h: [point('2026-10-03T10:00:00Z', 0.5, 0.25)], daily: [] }],
    ['/analytics/topics', { status: 'PASS', engine: 'BERTrend', items: [], detail: null }],
    ['/analytics/trends', { status: 'PASS', temporal_status: 'PASS', engine: 'BERTrend', fallback: false, items: [], detail: null }],
    ['/network/graph', { nodes: [], edges: [], node_count: 0, edge_count: 0 }],
    ['/network/summary', { summary: { nodes: 5, edges: 7, density: 0.1, communities: 2, metrics: [], interpretation: '' } }],
  ])
  renderPage(<OverviewPage />, '/dashboard')

  expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
  expect(screen.getByText('446')).toBeInTheDocument()
  expect(screen.getByText('4 replay kept separate')).toBeInTheDocument()
  // latest positive share and its change vs the previous window
  expect(screen.getByText('50.0')).toBeInTheDocument()
  expect(screen.getByText('+10.0 pp')).toBeInTheDocument()

  const sourcesPanel = (await screen.findByText('Sources')).closest('section')!
  expect(within(sourcesPanel).getByText('No credentials')).toBeInTheDocument()
  expect(within(sourcesPanel).getByText('Every 2m')).toBeInTheDocument()
  expect(within(sourcesPanel).getByText('No sources')).toBeInTheDocument()
  expect(within(sourcesPanel).getByText('296')).toBeInTheDocument()
})
