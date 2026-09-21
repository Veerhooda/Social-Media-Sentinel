import { AlertCircle, Bell, Menu, Search } from 'lucide-react'
import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { HealthResponse, SchedulerStatus } from '../types/system'
import { StatusBadge } from '../components/StatusBadge'

export function TopBar({ health, jobs, onMenu }: { health?: HealthResponse; jobs?: SchedulerStatus; onMenu: () => void }) {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const failures = jobs?.jobs.filter((job) => job.status === 'FAIL') ?? []
  const submit = (event: FormEvent) => {
    event.preventDefault()
    navigate(`/live-feed${search ? `?q=${encodeURIComponent(search)}` : ''}`)
  }
  const sourceCount = (platform: string) => (health?.platforms ?? []).find((item) => item.platform === platform)?.real_event_count ?? 0
  return (
    <header className="topbar">
      <button type="button" className="topbar__menu" onClick={onMenu} aria-label="Open navigation"><Menu size={20} /></button>
      <form className="global-search" onSubmit={submit}>
        <Search size={17} aria-hidden="true" />
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search posts, topics, users…" aria-label="Search posts, topics, and users" />
      </form>
      <div className="topbar__actions">
        <div className="topbar__sources" aria-label="Real collected events by platform">
          <span title={health?.x_api.status === 'PASS' ? 'X client configured' : 'X collector paused'}><b>X</b>{sourceCount('x')}</span>
          <span title={health?.telegram_api.status === 'PASS' ? 'Telegram session configured' : 'Telegram collector paused'}><b>TG</b>{sourceCount('telegram')}</span>
        </div>
        <StatusBadge status={health?.database.status ?? 'unavailable'} label={health?.database.status === 'PASS' ? 'LOCAL DATA' : 'DATABASE OFFLINE'} />
        <span className="event-count">{health?.event_count ?? '—'} events</span>
        <button type="button" className="icon-button" aria-label={failures.length ? `${failures.length} failed jobs` : 'No failed job alerts'}>
          {failures.length ? <AlertCircle size={19} /> : <Bell size={19} />}
          {failures.length > 0 && <span className="notification-dot" />}
        </button>
      </div>
    </header>
  )
}
