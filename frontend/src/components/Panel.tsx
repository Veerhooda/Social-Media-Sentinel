import type { ReactNode } from 'react'

interface PanelProps {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  footer?: ReactNode
  flush?: boolean
  className?: string
  children: ReactNode
  id?: string
}

export function Panel({ title, description, actions, footer, flush, className = '', children, id }: PanelProps) {
  return (
    <section className={`panel ${className}`.trim()} id={id} aria-label={typeof title === 'string' ? title : undefined}>
      {(title || actions) && (
        <header className="panel__header">
          <div>
            {title && <h2>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
          {actions && <div className="panel__actions">{actions}</div>}
        </header>
      )}
      <div className={`panel__body ${flush ? 'panel__body--flush' : ''}`}>{children}</div>
      {footer && <footer className="panel__footer">{footer}</footer>}
    </section>
  )
}
