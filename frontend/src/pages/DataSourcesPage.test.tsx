import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { DataSourcesPage } from './DataSourcesPage'

afterEach(() => vi.unstubAllGlobals())

it('separates implemented platforms from coming-soon sources', async () => {
  const health = {
    status: 'DEGRADED',
    database: { status: 'PASS', detail: 'PostgreSQL reachable' },
    x_api: { status: 'SKIPPED', detail: 'Collector paused' },
    telegram_api: { status: 'PASS', detail: 'Session configured' },
    youtube_api: { status: 'SKIPPED', detail: 'YOUTUBE_API_KEY is not configured' },
    scheduler: { status: 'SKIPPED', detail: 'Disabled' },
    analytics: { status: 'SKIPPED', detail: 'Disabled' },
    event_count: 303,
    real_event_count: 299,
    replay_event_count: 4,
    updated_at: '2026-09-21T00:00:00Z',
    platforms: [
      { platform: 'x', event_count: 300, real_event_count: 296, replay_event_count: 4, latest_created_at: null, latest_collected_at: '2026-09-20T18:00:00Z' },
      { platform: 'telegram', event_count: 3, real_event_count: 3, replay_event_count: 0, latest_created_at: null, latest_collected_at: '2026-09-20T18:30:00Z' },
    ],
  }
  const jobs = { enabled: false, running: false, started_at: null, stopped_at: null, jobs: [] }
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => Promise.resolve(new Response(JSON.stringify(String(input).endsWith('/health') ? health : jobs), { status: 200 }))))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><DataSourcesPage /></MemoryRouter></QueryClientProvider>)

  expect(await screen.findByText('Telegram')).toBeInTheDocument()
  expect(screen.getAllByText('STORED DATA')).toHaveLength(2)
  expect(screen.getAllByText('COMING SOON')).toHaveLength(1)
  expect(screen.getByText('YouTube')).toBeInTheDocument()
  expect(screen.getByText('Comment polling (not a live stream)')).toBeInTheDocument()
  expect(screen.getByText('Adapter implemented; API key not configured.')).toBeInTheDocument()
  expect(screen.getByText('Meta platforms')).toBeInTheDocument()
  expect(screen.queryByText('Never')).not.toBeInTheDocument()
})
