export type StatusTone = 'ok' | 'warn' | 'err' | 'idle' | 'accent' | 'neutral'

/** Maps backend status vocabulary to a semantic tone. Text is always shown next to the colour. */
export function statusTone(status: string): StatusTone {
  const normalized = status.toLowerCase()
  if (['pass', 'live', 'running', 'rising', 'sustained', 'completed', 'available', 'ok', 'collecting'].includes(normalized)) return 'ok'
  if (['degraded', 'pending', 'queued', 'insufficient_data', 'partial', 'emerging', 'warning'].includes(normalized)) return 'warn'
  if (['fail', 'failed', 'error', 'offline', 'unavailable'].includes(normalized)) return 'err'
  if (['replay', 'mixed', 'first_observation'].includes(normalized)) return 'accent'
  if (['skipped', 'idle', 'paused', 'cancelled', 'cooling', 'disabled'].includes(normalized)) return 'idle'
  return 'neutral'
}

export function humanStatus(status: string) {
  const text = status.replaceAll('_', ' ').toLowerCase()
  return text.charAt(0).toUpperCase() + text.slice(1)
}
