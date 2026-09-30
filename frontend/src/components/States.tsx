import { AlertTriangle, Database, WifiOff } from 'lucide-react'

export function LoadingState({ label = 'Loading analytics…' }: { label?: string }) {
  return (
    <div className="state state--loading" role="status">
      <span className="state__label">{label}</span>
      <div className="skeleton-layout" aria-hidden="true">
        <span className="skeleton-line skeleton-line--short" />
        <span className="skeleton-block" />
        <span className="skeleton-block skeleton-block--small" />
      </div>
    </div>
  )
}

export function EmptyState({ title = 'No data in this window', detail }: { title?: string; detail?: string }) {
  return (
    <div className="state">
      <Database size={24} aria-hidden="true" />
      <strong>{title}</strong>
      {detail && <span>{detail}</span>}
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'The backend request failed.'
  return (
    <div className="state state--error" role="alert">
      <AlertTriangle size={24} aria-hidden="true" />
      <strong>Unable to load analytics</strong>
      <span>{message}</span>
    </div>
  )
}

export function UnavailableState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="state state--unavailable">
      <WifiOff size={24} aria-hidden="true" />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  )
}
