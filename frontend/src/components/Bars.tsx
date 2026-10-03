import { useEffect, useState } from 'react'

export interface BarItem {
  label: string
  value: number
  display?: string
  color?: string
}

/** Horizontal bars that grow in on mount and animate between updates. */
export function Bars({ items, max, label }: { items: BarItem[]; max?: number; label: string }) {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const id = window.requestAnimationFrame?.(() => setReady(true))
    return () => { if (id) window.cancelAnimationFrame(id) }
  }, [])
  const top = max ?? Math.max(...items.map((item) => item.value), 0)
  return (
    <div className="bars" role="list" aria-label={label}>
      {items.map((item) => (
        <div className="bar" role="listitem" key={item.label}>
          <span className="truncate" title={item.label}>{item.label}</span>
          <div className="bar__track">
            <div className="bar__fill" style={{ width: ready && top > 0 ? `${(item.value / top) * 100}%` : '0%', background: item.color }} />
          </div>
          <b>{item.display ?? item.value.toLocaleString('en')}</b>
        </div>
      ))}
    </div>
  )
}

export function StackBar({ parts, label }: { parts: { key: string; value: number; color: string; label: string }[]; label: string }) {
  const total = parts.reduce((sum, part) => sum + part.value, 0)
  return (
    <div className="stack" role="img" aria-label={`${label}: ${parts.map((part) => `${part.label} ${total ? Math.round((part.value / total) * 100) : 0}%`).join(', ')}`}>
      {parts.map((part) => <i key={part.key} style={{ width: total ? `${(part.value / total) * 100}%` : 0, background: part.color }} title={`${part.label} ${total ? Math.round((part.value / total) * 100) : 0}%`} />)}
    </div>
  )
}
