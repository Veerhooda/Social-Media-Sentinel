import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it } from 'vitest'
import { LandingPage } from './LandingPage'

afterEach(cleanup)

it('leads into the existing dashboard without presenting illustrative previews as live data', () => {
  render(<MemoryRouter><LandingPage /></MemoryRouter>)
  expect(screen.getByRole('heading', { name: /The conversation.*beneath the conversation/i })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Enter the dashboard/i })).toHaveAttribute('href', '/dashboard')
  expect(screen.getByRole('link', { name: /Explore the platform/i })).toHaveAttribute('href', '#platform')
  expect(screen.getByLabelText('Illustrative previews of Social Sentinel analytics')).toBeInTheDocument()
})

it('opens a usable mobile navigation menu', async () => {
  const { container } = render(<MemoryRouter><LandingPage /></MemoryRouter>)
  const toggle = container.querySelector<HTMLButtonElement>('.landing-nav__toggle')!
  expect(toggle).toHaveAttribute('aria-expanded', 'false')
  fireEvent.click(toggle)
  expect(toggle).toHaveAttribute('aria-expanded', 'true')
  fireEvent.click(screen.getByRole('link', { name: 'Capabilities' }))
  expect(toggle).toHaveAttribute('aria-expanded', 'false')
})
