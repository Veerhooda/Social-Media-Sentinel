import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { DemographicsPage } from './DemographicsPage'

afterEach(() => vi.unstubAllGlobals())

const payload = {
  status: 'AVAILABLE',
  detail: '3/4 demographic dimensions available',
  total_subjects: 4,
  dimensions: {
    age: {
      dimension: 'age',
      status: 'UNAVAILABLE',
      detail: 'age inference unavailable: no validated age model is configured',
      total_subjects: 4,
      unknown_count: 4,
      segments: [],
      updated_at: null,
    },
    geography: {
      dimension: 'geography',
      status: 'AVAILABLE',
      detail: 'aggregate of normalized public location strings',
      total_subjects: 4,
      unknown_count: 2,
      segments: [
        { label: 'India', count: 2, share: 0.5, avg_confidence: 0.9 },
        { label: 'Unknown', count: 2, share: 0.5, avg_confidence: null },
      ],
      updated_at: '2026-09-21T00:00:00Z',
    },
    language: {
      dimension: 'language',
      status: 'AVAILABLE',
      detail: 'platform-observed codes preferred',
      total_subjects: 4,
      unknown_count: 0,
      segments: [{ label: 'en', count: 4, share: 1, avg_confidence: 1 }],
      updated_at: '2026-09-21T00:00:00Z',
    },
    profession: {
      dimension: 'profession',
      status: 'INSUFFICIENT_DATA',
      detail: 'no subject carried classifiable professional signals',
      total_subjects: 4,
      unknown_count: 4,
      segments: [],
      updated_at: null,
    },
  },
  updated_at: '2026-09-21T00:00:00Z',
}

function renderPage() {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }))),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DemographicsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

it('renders aggregate dimensions with unknown cohorts, never individuals', async () => {
  renderPage()
  expect(await screen.findByText('Audience Demographics')).toBeInTheDocument()
  expect(screen.getByText('Age Distribution')).toBeInTheDocument()
  expect(screen.getByText('Age estimates unavailable')).toBeInTheDocument()
  expect(screen.getByText('Geographic Distribution')).toBeInTheDocument()
  expect(screen.getByText('India')).toBeInTheDocument()
  expect(screen.getByText(/Unknown \/ insufficient evidence: 2/)).toBeInTheDocument()
  expect(screen.getByText('Language Distribution')).toBeInTheDocument()
  expect(screen.getByText('Professional Interests')).toBeInTheDocument()
  expect(screen.getByText('Insufficient data')).toBeInTheDocument()
})
