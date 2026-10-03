import { useEffect, useRef, useState } from 'react'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** Tweens from the previously shown value to the new one. Renders the final value immediately in tests/reduced motion. */
export function AnimatedNumber({ value, format = (n) => Math.round(n).toLocaleString('en'), duration = 700 }: {
  value: number
  format?: (value: number) => string
  duration?: number
}) {
  const [shown, setShown] = useState(value)
  const from = useRef(value)
  const frame = useRef(0)
  useEffect(() => {
    const start = from.current
    if (start === value || prefersReducedMotion() || typeof window.requestAnimationFrame !== 'function') {
      from.current = value
      setShown(value)
      return
    }
    const began = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - began) / duration)
      const eased = 1 - (1 - t) ** 3
      const current = start + (value - start) * eased
      from.current = current
      setShown(current)
      if (t < 1) frame.current = window.requestAnimationFrame(tick)
    }
    frame.current = window.requestAnimationFrame(tick)
    return () => window.cancelAnimationFrame(frame.current)
  }, [value, duration])
  return <>{format(shown)}</>
}
