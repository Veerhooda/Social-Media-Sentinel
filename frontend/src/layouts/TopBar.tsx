import { Menu, Search } from 'lucide-react'
import type { FormEvent } from 'react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Status } from '../components/Status'
import { useSystem } from '../hooks/useApiQueries'
import { timeAgo } from '../utils/format'

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const [health, jobs] = useSystem()
  const [params] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')
  const input = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        input.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const q = search.trim()
    navigate(`/live-feed${q ? `?q=${encodeURIComponent(q)}` : ''}`)
  }

  const latest = (health.data?.platforms ?? [])
    .map((platform) => platform.latest_collected_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1)
  const failures = jobs.data?.jobs.filter((job) => job.status === 'FAIL') ?? []
  const running = Boolean(jobs.data?.running)
  const recent = latest ? Date.now() - new Date(latest).getTime() < 15 * 60_000 : false

  return (
    <header className="topbar">
      <button type="button" className="topbar__menu" onClick={onMenu} aria-label="Open navigation"><Menu size={16} /></button>
      <form className="search" onSubmit={submit} role="search">
        <Search size={15} aria-hidden="true" />
        <input ref={input} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search conversations" aria-label="Search conversations" />
        <kbd>⌘K</kbd>
      </form>
      <div className="topbar__status">
        {failures.length > 0 && <Link to="/collection-status"><Status status="fail" label={`${failures.length} job${failures.length > 1 ? 's' : ''} failing`} /></Link>}
        {health.error ? <Status status="offline" label="API offline" /> : (
          <Link to="/data-sources" title={latest ? `Last event collected ${new Date(latest).toLocaleString()}` : undefined}>
            <Status
              status={running ? 'running' : 'paused'}
              live={running && recent}
              label={running ? `Collecting${latest ? ` · last event ${timeAgo(latest)}` : ''}` : 'Collection paused'}
            />
          </Link>
        )}
      </div>
    </header>
  )
}
