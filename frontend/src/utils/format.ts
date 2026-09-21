export const formatNumber = (value: number) =>
  new Intl.NumberFormat('en', { notation: value >= 10_000 ? 'compact' : 'standard', maximumFractionDigits: 1 }).format(value)

export const formatPercent = (value: number | null, digits = 1) =>
  value == null ? 'Unavailable' : `${(value * 100).toFixed(digits)}%`

export const formatDateTime = (value: string | null | undefined) =>
  value
    ? new Intl.DateTimeFormat('en', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(new Date(value))
    : 'Not available'

export const timeAgo = (value: string | null | undefined) => {
  if (!value) return 'never'
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  return `${Math.floor(minutes / 60)}h ago`
}

export const sentenceCase = (value: string) =>
  value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())


export const formatDuration = (seconds: number | null | undefined) => {
  if (seconds == null) return 'Not available'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours}h ${minutes % 60}m`
  return `${Math.floor(hours / 24)}d ${hours % 24}h`
}
