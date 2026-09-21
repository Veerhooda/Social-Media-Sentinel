import { render, screen } from '@testing-library/react'
import { Activity } from 'lucide-react'
import { describe, expect, it } from 'vitest'
import { MetricCard } from './MetricCard'
import { EmptyState, ErrorState, LoadingState, UnavailableState } from './States'
import { StatusBadge } from './StatusBadge'
import { SystemStateStrip } from './SystemStateStrip'

describe('shared states and metrics', () => {
  it('renders a metric from supplied data', () => {
    render(<MetricCard label="Live Events" value="58" detail="stored events" icon={Activity} />)
    expect(screen.getByText('58')).toBeInTheDocument()
    expect(screen.getByText('stored events')).toBeInTheDocument()
  })

  it('renders honest loading, error and unavailable states', () => {
    const { rerender } = render(<LoadingState label="Loading analytics" />)
    expect(screen.getByText('Loading analytics')).toBeInTheDocument()
    rerender(<ErrorState error={new Error('Backend offline')} />)
    expect(screen.getByText('Backend offline')).toBeInTheDocument()
    rerender(<UnavailableState title="Not implemented" detail="No adapter exists" />)
    expect(screen.getByText('No adapter exists')).toBeInTheDocument()
    rerender(<EmptyState />)
    expect(screen.getByText('No data in this window')).toBeInTheDocument()
  })

  it('labels replay without presenting it as live', () => {
    render(<StatusBadge status="replay" />)
    expect(screen.getByText('replay')).toBeInTheDocument()
  })

  it('summarizes real X and Telegram rows without implying an active collector', () => {
    render(<SystemStateStrip health={{
      status: 'DEGRADED',
      database: { status: 'PASS', detail: 'PostgreSQL reachable' },
      x_api: { status: 'SKIPPED', detail: 'Collector paused' },
      telegram_api: { status: 'PASS', detail: 'Session configured' },
      scheduler: { status: 'SKIPPED', detail: 'Disabled' },
      analytics: { status: 'SKIPPED', detail: 'Disabled' },
      event_count: 303,
      real_event_count: 299,
      replay_event_count: 4,
      updated_at: new Date().toISOString(),
      platforms: [
        { platform: 'x', event_count: 300, real_event_count: 296, replay_event_count: 4, latest_created_at: null, latest_collected_at: null },
        { platform: 'telegram', event_count: 3, real_event_count: 3, replay_event_count: 0, latest_created_at: null, latest_collected_at: null },
      ],
    }} />)
    expect(screen.getByText('Mixed real and replay data')).toBeInTheDocument()
    expect(screen.getByText('296 real events')).toBeInTheDocument()
    expect(screen.getByText('3 real events')).toBeInTheDocument()
    expect(screen.getByText('Paused')).toBeInTheDocument()
  })
})
