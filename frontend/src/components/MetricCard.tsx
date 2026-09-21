import type { LucideIcon } from 'lucide-react'
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import type { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: ReactNode
  detail: string
  change?: number | null
  icon: LucideIcon
  tone?: 'orange' | 'blue' | 'green' | 'pink' | 'purple'
  unavailable?: boolean
}

export function MetricCard({ label, value, detail, change, icon: Icon, tone = 'orange', unavailable }: MetricCardProps) {
  const ChangeIcon = change == null ? Minus : change >= 0 ? ArrowUpRight : ArrowDownRight
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__top">
        <span>{label}</span>
        <span className="metric-card__icon"><Icon size={18} aria-hidden="true" /></span>
      </div>
      <strong className={unavailable ? 'metric-card__value--muted' : ''}>{value}</strong>
      <div className="metric-card__detail">
        {change !== undefined && (
          <span className={change == null ? 'change-neutral' : change >= 0 ? 'change-positive' : 'change-negative'}>
            <ChangeIcon size={13} aria-hidden="true" />
            {change == null ? 'Unavailable' : `${Math.abs(change * 100).toFixed(1)}%`}
          </span>
        )}
        <span>{detail}</span>
      </div>
    </article>
  )
}

