import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { TrendsPage } from './TrendsPage'

afterEach(() => vi.unstubAllGlobals())

const topic = (id: number, name: string, volume: number, velocity: number | null, status: string) => ({
  topic_id: id, topic: name, keywords: name.toLowerCase().split(' '), volume, growth: velocity == null ? null : -0.625, velocity, acceleration: null,
  window_start: '2026-09-20T15:45:00Z', window_end: '2026-09-20T16:00:00Z', status, sentiment: { neutral: 1 }, source: 'BERTrend/0.4.18',
})

it('shows backend topic status, never inferring direction from one window, and filters/sorts', async () => {
  const items = [topic(45, 'Model safety', 3, -6.66, 'cooling'), topic(46, 'Chip exports', 9, null, 'emerging')]
  stubApi([
    ['/analytics/topics', { status: 'PASS', engine: 'BERTrend/0.4.18', items, detail: null }],
    ['/analytics/trends', { status: 'PASS', temporal_status: 'PASS', engine: 'BERTrend/0.4.18', fallback: false, items, detail: null }],
  ])
  renderPage(<TrendsPage />)
  expect(await screen.findByText('Model safety')).toBeInTheDocument()
  expect(screen.getAllByText('Cooling').length).toBeGreaterThan(0)
  expect(screen.getByText('-6.66')).toBeInTheDocument()
  expect(screen.getAllByText('First seen').length).toBeGreaterThan(0)

  const rows = () => screen.getAllByRole('row').slice(1).map((row) => row.textContent)
  expect(rows()[0]).toContain('Chip exports')
  fireEvent.click(screen.getByRole('button', { name: /Volume/ }))
  expect(rows()[0]).toContain('Model safety')
  fireEvent.change(screen.getByLabelText('Filter topics'), { target: { value: 'chip' } })
  expect(rows()).toHaveLength(1)
})
