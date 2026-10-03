import { humanStatus, statusTone } from '../utils/status'

export function Status({ status, label, live = false }: { status: string; label?: string; live?: boolean }) {
  const tone = statusTone(status)
  return (
    <span className={`status status--${tone} ${live ? 'is-live' : ''}`}>
      <i aria-hidden="true" />
      {label ?? humanStatus(status)}
    </span>
  )
}
