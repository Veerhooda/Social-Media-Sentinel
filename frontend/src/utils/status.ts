export type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral' | 'info' | 'replay'

export function statusTone(status: string): BadgeTone {
  const normalized = status.toLowerCase()
  if (['pass', 'live', 'running', 'rising', 'sustained'].includes(normalized)) return 'success'
  if (['degraded', 'emerging', 'pending', 'insufficient_data', 'cooling'].includes(normalized)) return 'warning'
  if (['fail', 'offline', 'unavailable'].includes(normalized)) return 'danger'
  if (normalized === 'replay' || normalized === 'mixed') return 'replay'
  if (normalized === 'skipped') return 'info'
  return 'neutral'
}
