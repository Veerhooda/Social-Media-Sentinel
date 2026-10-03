import { screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { DemographicsPage } from './DemographicsPage'

afterEach(() => vi.unstubAllGlobals())

const dimension = (name: string, status: string, unknown: number, segments: unknown[], detail = '') => ({ dimension: name, status, detail, total_subjects: 4, unknown_count: unknown, segments, updated_at: null })

it('renders aggregate dimensions only, with coverage and honest gaps', async () => {
  stubApi([['/analytics/demographics', {
    status: 'AVAILABLE', detail: '3/4 demographic dimensions available', total_subjects: 4, updated_at: null,
    dimensions: {
      age: dimension('age', 'UNAVAILABLE', 4, [], 'no validated age model is configured'),
      geography: dimension('geography', 'AVAILABLE', 2, [{ label: 'India', count: 2, share: 0.5, avg_confidence: 0.9 }, { label: 'Unknown', count: 2, share: 0.5, avg_confidence: null }]),
      language: dimension('language', 'AVAILABLE', 0, [{ label: 'en', count: 4, share: 1, avg_confidence: 1 }]),
      profession: dimension('profession', 'INSUFFICIENT_DATA', 4, [], 'no subject carried classifiable professional signals'),
    },
  }]])
  renderPage(<DemographicsPage />)
  expect(await screen.findByRole('heading', { name: 'Demographics' })).toBeInTheDocument()
  expect(screen.getByText('India')).toBeInTheDocument()
  expect(screen.getAllByText('100%').length).toBeGreaterThan(0) // India is 100% of accounts with country evidence
  expect(screen.getByText(/50% of accounts have enough evidence/)).toBeInTheDocument()
  expect(screen.getByText('Not available')).toBeInTheDocument()
  expect(screen.getByText('no validated age model is configured')).toBeInTheDocument()
  expect(screen.getByText('Not enough evidence yet')).toBeInTheDocument()
  expect(screen.queryByText('Unknown')).not.toBeInTheDocument()
})
