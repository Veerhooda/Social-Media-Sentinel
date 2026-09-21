import { Circle } from 'lucide-react'
import { statusTone, type BadgeTone } from '../utils/status'

export type { BadgeTone }

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const tone = statusTone(status)
  return (
    <span className={`status-badge status-badge--${tone}`}>
      <Circle size={7} fill="currentColor" aria-hidden="true" />
      {label ?? status.replaceAll('_', ' ')}
    </span>
  )
}
