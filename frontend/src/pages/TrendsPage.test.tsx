import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { TrendsPage } from './TrendsPage'

afterEach(() => vi.unstubAllGlobals())

it('renders backend topic status without inferring a different trend', async () => {
  const topic = { topic_id: 45, topic: 'Model safety', keywords: ['model', 'safety'], volume: 3, growth: -0.625, velocity: -6.66, acceleration: null, window_start: '2026-09-20T15:45:00Z', window_end: '2026-09-20T16:00:00Z', status: 'cooling', sentiment: { neutral: 1 }, source: 'BERTrend/0.4.18' }
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    const body = url.endsWith('/topics')
      ? { status: 'PASS', engine: 'BERTrend/0.4.18', items: [topic], detail: null }
      : { status: 'PASS', temporal_status: 'PASS', engine: 'BERTrend/0.4.18', fallback: false, items: [topic], detail: null }
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
  }))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><TrendsPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByText('Model safety')).toBeInTheDocument()
  expect(screen.getByText('cooling')).toBeInTheDocument()
  expect(screen.getByText('-6.66')).toBeInTheDocument()
})

