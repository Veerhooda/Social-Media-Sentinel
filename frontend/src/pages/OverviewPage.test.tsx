import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { OverviewPage } from './OverviewPage'

afterEach(() => vi.unstubAllGlobals())

function renderWithHealth(platforms: unknown[]) {
  const health = {
    status: 'PASS',
    database: { status: 'PASS', detail: 'PostgreSQL reachable' },
    x_api: { status: 'SKIPPED', detail: 'Collector paused' },
    telegram_api: { status: 'SKIPPED', detail: 'Collector paused' },
    scheduler: { status: 'SKIPPED', detail: 'Disabled' },
    analytics: { status: 'SKIPPED', detail: 'Disabled' },
    event_count: 1,
    real_event_count: 1,
    replay_event_count: 0,
    updated_at: '2026-09-21T00:00:00Z',
    platforms,
  }
  const emptyList = { items: [], count: 0, total: 0, offset: 0, limit: 1 }
  const emptySeries = { rolling_1h: [], daily: [] }
  const emptyTrends = { status: 'SKIPPED', temporal_status: 'INSUFFICIENT_DATA', engine: 'none', fallback: false, items: [], detail: null }
  const emptyNetwork = { summary: { nodes: 0, edges: 0, density: 0, communities: 0, metrics: [], interpretation: '' } }
  const emptyGraph = { nodes: [], edges: [], node_count: 0, edge_count: 0 }
  const jobs = { enabled: false, running: false, started_at: null, stopped_at: null, jobs: [] }
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      const body = url.includes('/health')
        ? health
        : url.includes('/system/jobs')
          ? jobs
          : url.includes('/events')
            ? emptyList
            : url.includes('/analytics/sentiment') || url.includes('/analytics/emotions')
              ? emptySeries
              : url.includes('/analytics/trends')
                ? emptyTrends
                : url.includes('/network/graph')
                  ? emptyGraph
                  : emptyNetwork
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

it('shows live badges only for platforms with stored data', async () => {
  renderWithHealth([
    { platform: 'x', event_count: 1, real_event_count: 1, replay_event_count: 0, latest_created_at: null, latest_collected_at: '2026-09-20T18:00:00Z' },
  ])
  expect(await screen.findByText('Data Sources')).toBeInTheDocument()
  expect(screen.getByText('LIVE DATA')).toBeInTheDocument()
  expect(screen.getByText('NO STORED DATA')).toBeInTheDocument()
})
