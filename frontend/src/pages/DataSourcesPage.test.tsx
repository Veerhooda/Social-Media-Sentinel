import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { health, jobs, stubApi } from '../test/fetch'
import { renderPage } from '../test/render'
import { DataSourcesPage } from './DataSourcesPage'

afterEach(() => vi.unstubAllGlobals())

const source = { source_id: 's1', platform: 'telegram', target: 'durov', label: null, enabled: true, last_run_at: '2026-10-03T10:00:00Z', last_status: 'PASS', last_detail: 'fetched 12 new messages; stored 12', last_fetched: 12, last_stored: 12, total_stored: 40, created_at: null }
const overview = {
  scheduler_enabled: true,
  scheduler_running: false,
  platforms: [
    { platform: 'x', credentials_configured: false, credential_detail: 'X_BEARER_TOKEN is not set in .env', job_name: 'x_recent_search', interval_seconds: 60, sources: [] },
    { platform: 'telegram', credentials_configured: true, credential_detail: 'ok', job_name: 'telegram_collection', interval_seconds: 120, sources: [source] },
    { platform: 'youtube', credentials_configured: true, credential_detail: 'ok', job_name: 'youtube_collection', interval_seconds: 60, sources: [] },
  ],
}

it('lists sources per platform, explains missing credentials and adds a source', async () => {
  const calls = stubApi([
    ['/health', health()],
    ['/system/jobs', jobs([], false)],
    ['/sources', (init?: RequestInit) => (init?.method === 'POST' ? { ...source, source_id: 's2', platform: 'youtube', target: 'dQw4w9WgXcQ' } : overview)],
  ])
  renderPage(<DataSourcesPage />)

  expect(await screen.findByText('durov')).toBeInTheDocument()
  expect(screen.getByText('fetched 12 new messages; stored 12')).toBeInTheDocument()
  expect(screen.getByText('X_BEARER_TOKEN is not set in .env')).toBeInTheDocument()
  expect(screen.getByText('Scheduler off · runs are manual')).toBeInTheDocument()
  expect(screen.getByRole('switch', { name: 'Disable durov' })).toHaveAttribute('aria-checked', 'true')

  fireEvent.change(screen.getByLabelText('Add YouTube source'), { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } })
  fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[2])
  await waitFor(() => expect(calls.some((call) => call.init?.method === 'POST' && call.url.endsWith('/sources'))).toBe(true))
  const body = JSON.parse(String(calls.find((call) => call.init?.method === 'POST')!.init!.body))
  expect(body).toEqual({ platform: 'youtube', target: 'https://youtu.be/dQw4w9WgXcQ', label: null })
})
