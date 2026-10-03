import { AlertTriangle } from 'lucide-react'
import type { ReactNode } from 'react'

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="skeleton" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <span /><span /><span /><span className="block" />
    </div>
  )
}

export function EmptyState({ title = 'No data in this window', detail, action }: { title?: string; detail?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {detail && <span>{detail}</span>}
      {action}
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'The request failed.'
  return (
    <div className="error" role="alert">
      <strong>Could not load this data</strong>
      <span>{message}</span>
    </div>
  )
}

export function Notice({ children, tone = 'warn' }: { children: ReactNode; tone?: 'warn' | 'error' }) {
  return <div className={`notice ${tone === 'error' ? 'notice--error' : ''}`} role={tone === 'error' ? 'alert' : 'status'}><AlertTriangle size={15} aria-hidden="true" /><div>{children}</div></div>
}
