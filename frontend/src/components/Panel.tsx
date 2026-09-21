import type { ReactNode } from 'react'

interface PanelProps {
  title?: string
  subtitle?: string
  action?: ReactNode
  className?: string
  children: ReactNode
}

export function Panel({ title, subtitle, action, className = '', children }: PanelProps) {
  return (
    <section className={`panel ${className}`.trim()}>
      {(title || action) && (
        <header className="panel__header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="panel__content">{children}</div>
    </section>
  )
}

