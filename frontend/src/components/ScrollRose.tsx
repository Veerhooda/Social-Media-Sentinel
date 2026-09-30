import { useEffect, useRef, useState } from 'react'

export function ScrollRose() {
  const sectionRef = useRef<HTMLElement>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      const section = sectionRef.current
      if (!section) return
      const rect = section.getBoundingClientRect()
      const travel = Math.max(1, rect.height - window.innerHeight)
      setProgress(Math.max(0, Math.min(1, -rect.top / travel)))
    }
    const schedule = () => { if (!frame) frame = window.requestAnimationFrame(update) }
    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => { window.removeEventListener('scroll', schedule); window.removeEventListener('resize', schedule); if (frame) window.cancelAnimationFrame(frame) }
  }, [])

  return (
    <section ref={sectionRef} className="rose-scroll" aria-labelledby="rose-scroll-title" data-progress={progress.toFixed(2)}>
      <div className="rose-scroll__sticky">
        <div className="rose-scroll__visual" style={{ '--rose-progress': progress } as React.CSSProperties} aria-hidden="true">
          <img src="/images/purple-rose.jpg" alt="" loading="lazy" />
        </div>
        <div className="rose-scroll__copy">
          <span className="rose-scroll__eyebrow">A DEEPER KIND OF SIGNAL</span>
          <h2 id="rose-scroll-title">Watch a narrative <em>unfold.</em></h2>
          <p>Follow conversations from their first appearance to the moments they gather momentum. Social Sentinel keeps the chronology—and the uncertainty—in view.</p>
          <span className="rose-scroll__caption">SCROLL TO REVEAL THE STORY</span>
        </div>
      </div>
    </section>
  )
}
