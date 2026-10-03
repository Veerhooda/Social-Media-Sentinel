import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Bars } from './Bars'
import { Delta, Stat } from './Stat'
import { EmptyState, ErrorState, LoadingState, Notice } from './States'
import { Status } from './Status'

describe('shared components', () => {
  it('renders a stat from supplied data, linking when asked', () => {
    render(<MemoryRouter><Stat label="Events stored" value={1234} meta="across 3 platforms" to="/live-feed" /></MemoryRouter>)
    expect(screen.getByText('1,234')).toBeInTheDocument()
    expect(screen.getByText('across 3 platforms')).toBeInTheDocument()
    expect(screen.getByRole('link')).toHaveAttribute('href', '/live-feed')
  })

  it('shows a dash instead of inventing a value', () => {
    render(<Stat label="Positive" value={null} />)
    expect(screen.getByText('–')).toBeInTheDocument()
  })

  it('colours deltas by meaning and hides missing comparisons', () => {
    const { rerender, container } = render(<Delta value={2.04} />)
    expect(screen.getByText('+2.0 pp')).toHaveClass('delta--up')
    rerender(<Delta value={2} invert />)
    expect(screen.getByText('+2.0 pp')).toHaveClass('delta--down')
    rerender(<Delta value={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('always pairs status colour with text', () => {
    render(<Status status="SKIPPED" />)
    expect(screen.getByText('Skipped')).toBeInTheDocument()
  })

  it('renders loading, empty, error and notice states', () => {
    const { rerender } = render(<LoadingState label="Loading analytics" />)
    expect(screen.getByText('Loading analytics')).toBeInTheDocument()
    rerender(<ErrorState error={new Error('Backend offline')} />)
    expect(screen.getByText('Backend offline')).toBeInTheDocument()
    rerender(<EmptyState />)
    expect(screen.getByText('No data in this window')).toBeInTheDocument()
    rerender(<Notice tone="error">Key missing</Notice>)
    expect(screen.getByRole('alert')).toHaveTextContent('Key missing')
  })

  it('labels every bar with its value', () => {
    render(<Bars label="Emotions" items={[{ label: 'Joy', value: 0.4, display: '40%' }, { label: 'Anger', value: 0.1, display: '10%' }]} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('40%')).toBeInTheDocument()
  })
})
