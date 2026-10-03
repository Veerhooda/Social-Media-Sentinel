import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AnimatedNumber } from './AnimatedNumber'

export type StatTone = 'default' | 'pos' | 'neg' | 'sar' | 'accent'

interface StatProps {
  label: string
  value: number | null | undefined
  format?: (value: number) => string
  unit?: string
  meta?: ReactNode
  tone?: StatTone
  to?: string
}

export function Stat({ label, value, format, unit, meta, tone = 'default', to }: StatProps) {
  const body = (
    <>
      <span className="stat__label">{label}</span>
      <strong className="stat__value">
        {value == null ? '–' : <AnimatedNumber value={value} format={format} />}
        {value != null && unit && <small>{unit}</small>}
      </strong>
      <span className="stat__meta">{meta}</span>
    </>
  )
  const className = `stat ${tone !== 'default' ? `stat--${tone}` : ''}`
  return to ? <Link to={to} className={className}>{body}</Link> : <div className={className}>{body}</div>
}

/** Percentage-point change. Only render when a real prior value exists. */
export function Delta({ value, suffix = ' pp', invert = false }: { value: number | null | undefined; suffix?: string; invert?: boolean }) {
  if (value == null || Number.isNaN(value)) return null
  const rounded = Math.round(value * 10) / 10
  const good = invert ? rounded < 0 : rounded > 0
  const tone = rounded === 0 ? 'flat' : good ? 'up' : 'down'
  return <span className={`delta delta--${tone}`}>{rounded > 0 ? '+' : ''}{rounded.toFixed(1)}{suffix}</span>
}

export function Stats({ children, label }: { children: ReactNode; label?: string }) {
  return <section className="stats" aria-label={label}>{children}</section>
}
