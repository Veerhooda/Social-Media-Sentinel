import { AlertCircle, ArrowUpRight, Menu, Search } from 'lucide-react'
import { FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { HealthResponse, SchedulerStatus } from '../types/system'
import { StatusBadge } from '../components/StatusBadge'

export function TopBar({ health, jobs, onMenu }: { health?: HealthResponse; jobs?: SchedulerStatus; onMenu: () => void }) {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const title = location.pathname === '/dashboard' ? 'Overview' : location.pathname.startsWith('/trends/') ? 'Topic detail' : ({
    '/live-feed': 'Conversation feed', '/sentiment': 'Sentiment & emotion', '/trends': 'Trends & topics',
    '/network': 'Interaction map', '/demographics': 'Demographics', '/timeline': 'Timeline',
    '/data-sources': 'Data sources', '/collection-status': 'Collection status',
  } as Record<string, string>)[location.pathname] ?? 'Social Sentinel'
  const failures = jobs?.jobs.filter((job) => job.status === 'FAIL') ?? []
  const submit = (event: FormEvent) => {
    event.preventDefault()
    navigate(`/live-feed${search ? `?q=${encodeURIComponent(search)}` : ''}`)
  }
  const sourceCount = (platform: string) => (health?.platforms ?? []).find((item) => item.platform === platform)?.real_event_count ?? 0
  return (
    <header className="topbar">
      <button type="button" className="topbar__menu" onClick={onMenu} aria-label="Open navigation"><Menu size={20} /></button>
      <h1 className="topbar__title">{title}</h1>
      <form className="global-search" onSubmit={submit}>
        <Search size={17} aria-hidden="true" />
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search collected conversations…" aria-label="Search collected conversations" />
        <button type="submit" aria-label="Search feed"><ArrowUpRight size={17} /></button>
      </form>
      <div className="topbar__actions">
        <StatusBadge status={health?.database.status ?? 'unavailable'} label={health?.database.status === 'PASS' ? 'LOCAL DATA' : 'DATABASE OFFLINE'} />
        <span className="event-count">{sourceCount('x') + sourceCount('telegram') + sourceCount('youtube')} real events</span>
        {failures.length > 0 && <span className="topbar__alert" role="status"><AlertCircle size={17} />{failures.length} job failures</span>}
      </div>
    </header>
  )
}
