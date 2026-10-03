import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { health, jobs, stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { CollectionStatusPage } from './CollectionStatusPage'

afterEach(() => vi.unstubAllGlobals())

const job = (name: string, status: string, detail: string | null = null) => ({
  name, interval_seconds: 120, status, last_started_at: '2026-10-03T10:00:00Z', last_finished_at: '2026-10-03T10:00:02Z', next_run_at: null,
  processed_count: 3, total_processed_count: 30, duration_ms: 2000, error: status === 'FAIL' ? 'boom' : null, detail, run_count: 10, overlap_skips: 0,
})

it('lists jobs with readable names and runs one on demand', async () => {
  const calls = stubApi([
    ['/health', health()],
    ['/run', job('telegram_collection', 'PASS')],
    ['/system/jobs', jobs([job('x_recent_search', 'SKIPPED', 'X_BEARER_TOKEN is not configured'), job('telegram_collection', 'PASS'), job('graph_refresh', 'FAIL')])],
  ])
  renderPage(<CollectionStatusPage />)
  expect(await screen.findByText('Telegram collection')).toBeInTheDocument()
  expect(screen.getByText('X collection')).toBeInTheDocument()
  expect(screen.getByText('Interaction graph')).toBeInTheDocument()
  expect(screen.getByText('Skipped')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Run Telegram collection now' }))
  await waitFor(() => expect(calls.some((call) => call.init?.method === 'POST' && call.url.endsWith('/system/jobs/telegram_collection/run'))).toBe(true))
})
