import { ChevronLeft, ChevronRight, Filter, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { PlatformBadge } from '../components/PlatformBadge'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useEnrichedEvents } from '../hooks/useApiQueries'
import type { EnrichedEvent } from '../types/events'
import type { EventFilters } from '../utils/dashboard'
import { formatDateTime, formatNumber, sentenceCase } from '../utils/format'

export function LiveFeedPage() {
  const [params, setParams] = useSearchParams()
  const searchFromUrl = params.get('q') ?? ''
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<EnrichedEvent | null>(null)
  const [filters, setFilters] = useState<EventFilters>({
    search: searchFromUrl, platform: 'all', sentiment: 'all', emotion: 'all', interaction: 'all',
  })
  const [debouncedSearch, setDebouncedSearch] = useState(searchFromUrl)
  useEffect(() => {
    const timer = window.setTimeout(() => { setDebouncedSearch(filters.search.trim()); setOffset(0) }, 300)
    return () => window.clearTimeout(timer)
  }, [filters.search])
  useEffect(() => { setFilters((current) => ({ ...current, search: searchFromUrl })) }, [searchFromUrl])
  const query = useMemo(() => ({
    offset,
    platform: filters.platform === 'all' ? undefined : filters.platform,
    q: debouncedSearch || undefined,
    sentiment: filters.sentiment === 'all' ? undefined : filters.sentiment,
    emotion: filters.emotion === 'all' ? undefined : filters.emotion,
    interaction: filters.interaction === 'all' ? undefined : filters.interaction,
  }), [offset, filters.platform, filters.sentiment, filters.emotion, filters.interaction, debouncedSearch])
  const events = useEnrichedEvents(query)
  const filtered = events.data?.items ?? []
  const hasFilters = Boolean(filters.search.trim()) || [filters.platform, filters.sentiment, filters.emotion, filters.interaction].some((value) => value !== 'all')
  const filterIsUpdating = debouncedSearch !== filters.search.trim() || events.isPlaceholderData
  const clearFilters = () => {
    setOffset(0)
    setFilters({ search: '', platform: 'all', sentiment: 'all', emotion: 'all', interaction: 'all' })
    setParams({})
  }
  const hasReal = events.data?.items.some(({ event }) => !event.source_metadata.replay)
  const hasReplay = events.data?.items.some(({ event }) => Boolean(event.source_metadata.replay))
  const mode = hasReal && hasReplay ? 'mixed' : hasReal ? 'live' : hasReplay ? 'replay' : 'idle'
  if (events.isLoading) return <LoadingState label="Loading chronological event feed…" />
  if (events.error) return <ErrorState error={events.error} />
  return (
    <div className="page-stack">
      <PageHeader title="Conversation feed" subtitle="Stored canonical events ordered by source time, with persisted NLP analysis. New data is checked every five seconds." actions={<StatusBadge status={mode} label={mode === 'live' ? 'STORED REAL DATA' : mode === 'mixed' ? 'MIXED DATA' : undefined} />} />
      <Panel className="feed-panel" title="Collected conversations" subtitle={filterIsUpdating ? 'Updating results…' : `${events.data?.total ?? 0} matching stored events · filters and counts cover the database`} action={<div className="feed-panel__actions"><Filter size={17} aria-hidden="true" />{hasFilters && <button type="button" onClick={clearFilters}>Clear filters</button>}</div>}>
        <div className="filter-bar">
          <label className="feed-filter"><span>Search</span><input value={filters.search} maxLength={200} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="Text, author, hashtag" aria-label="Search event feed" /></label>
          <Select label="Platform" value={filters.platform} onChange={(value) => { setOffset(0); setFilters({ ...filters, platform: value }) }} options={['all', 'x', 'telegram', 'youtube']} />
          <Select label="Sentiment" value={filters.sentiment} onChange={(value) => { setOffset(0); setFilters({ ...filters, sentiment: value }) }} options={['all', 'positive', 'neutral', 'negative']} />
          <Select label="Emotion" value={filters.emotion} onChange={(value) => { setOffset(0); setFilters({ ...filters, emotion: value }) }} options={['all', 'excitement', 'approval', 'neutral', 'admiration', 'anxiety']} />
          <Select label="Interaction" value={filters.interaction} onChange={(value) => { setOffset(0); setFilters({ ...filters, interaction: value }) }} options={['all', 'post', 'comment', 'mention', 'reply', 'quote', 'repost', 'forward']} />
        </div>
        <div aria-live="polite" className="sr-only">{filterIsUpdating ? 'Updating results' : `${events.data?.total ?? 0} matching events`}</div>
        {filterIsUpdating ? <LoadingState label="Updating conversation results…" /> : filtered.length ? (
          <div className="event-table" role="table" aria-label="Canonical event feed">
            <div className="event-table__header" role="row"><span>Time</span><span>Source</span><span>Conversation</span><span>Analysis</span><span>Engagement</span></div>
            {filtered.map((item) => <EventRow key={item.event.event_id} item={item} onClick={() => setSelected(item)} />)}
          </div>
        ) : <EmptyState title="No events match these filters" detail="Clear a filter or try a different search across the stored corpus." />}
        <div className="pagination">
          <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}><ChevronLeft size={15} /> Newer</button>
          <span>{events.data?.total ? offset + 1 : 0}–{Math.min(offset + 50, events.data?.total ?? 0)} of {events.data?.total ?? 0}</span>
          <button type="button" disabled={offset + 50 >= (events.data?.total ?? 0)} onClick={() => setOffset(offset + 50)}>Older <ChevronRight size={15} /></button>
        </div>
      </Panel>
      {selected && <EventDrawer item={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function EventRow({ item, onClick }: { item: EnrichedEvent; onClick: () => void }) {
  const { event, analysis } = item
  const engagement = event.metrics.likes + event.metrics.shares + event.metrics.comments
  const activity = event.metrics.views ? `${formatNumber(event.metrics.views)} views` : formatNumber(engagement)
  return (
    <button className="event-row" type="button" role="row" onClick={onClick}>
      <time className="event-row__time">{formatDateTime(event.created_at)}</time>
      <div className="event-row__source"><PlatformBadge platform={event.platform} /><span>{event.author.username ? `@${event.author.username}` : event.author.display_name ?? 'Unknown author'}</span></div>
      <div className="event-row__content"><strong>{sentenceCase(event.interaction_type)}</strong><p>{event.content.text}</p></div>
      <div className="event-row__analysis">{analysis ? <><StatusBadge status={analysis.sentiment.label} /><span>{sentenceCase(analysis.emotions.primary_label ?? 'Unknown emotion')}</span>{analysis.irony.is_ironic && <em>Irony {Math.round(analysis.irony.confidence * 100)}%</em>}</> : <StatusBadge status="pending" label="Analysis pending" />}</div>
      <b className="event-row__engagement">{activity}</b>
    </button>
  )
}

function EventDrawer({ item, onClose }: { item: EnrichedEvent; onClose: () => void }) {
  const { event, analysis } = item
  const dialogRef = useRef<HTMLElement>(null)
  const onCloseRef = useRef(onClose)
  useEffect(() => { onCloseRef.current = onClose }, [onClose])
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const closeButton = dialogRef.current?.querySelector<HTMLButtonElement>('button[aria-label="Close event detail"]')
    closeButton?.focus()
    const onKeyDown = (keyboardEvent: KeyboardEvent) => {
      if (keyboardEvent.key === 'Escape') { keyboardEvent.preventDefault(); onCloseRef.current() }
      if (keyboardEvent.key !== 'Tab') return
      const controls = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? [])
      if (!controls.length) return
      const first = controls[0]
      const last = controls.at(-1)!
      if (keyboardEvent.shiftKey && document.activeElement === first) { keyboardEvent.preventDefault(); last.focus() }
      else if (!keyboardEvent.shiftKey && document.activeElement === last) { keyboardEvent.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => { document.removeEventListener('keydown', onKeyDown); previousFocus?.focus() }
  }, [])
  const sourceUrl = event.platform === 'x' && /^\d+$/.test(event.platform_post_id)
    ? `https://x.com/i/web/status/${event.platform_post_id}`
    : null
  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside ref={dialogRef} className="event-drawer" role="dialog" aria-modal="true" aria-label="Event details" onClick={(event) => event.stopPropagation()}>
        <header><div><PlatformBadge platform={item.event.platform} /><h2>Event Detail</h2></div><button type="button" onClick={onClose} aria-label="Close event detail"><X size={19} /></button></header>
        <section><span className="eyebrow">SOURCE EVENT</span><p className="drawer-text">{event.content.text}</p><dl><dt>Created</dt><dd>{formatDateTime(event.created_at)}</dd><dt>Collected</dt><dd>{formatDateTime(event.collected_at)}</dd><dt>Type</dt><dd>{event.interaction_type}</dd><dt>Source ID</dt><dd>{event.platform_post_id}</dd></dl>{sourceUrl && <a className="drawer-source-link" href={sourceUrl} target="_blank" rel="noopener noreferrer">Open original X post ↗</a>}</section>
        <section><span className="eyebrow">NLP ANALYSIS</span>{analysis ? <dl><dt>Sentiment</dt><dd>{sentenceCase(analysis.sentiment.label)} · {Math.round(analysis.sentiment.confidence * 100)}%</dd><dt>Primary emotion</dt><dd>{sentenceCase(analysis.emotions.primary_label ?? 'Unavailable')}</dd><dt>Irony</dt><dd>{analysis.irony.is_ironic ? 'Detected' : 'Not detected'} · {Math.round(analysis.irony.confidence * 100)}%</dd><dt>Stance</dt><dd>{analysis.stance.supported ? analysis.stance.label : 'Unsupported for arbitrary target'}</dd><dt>Topic</dt><dd>Per-event assignment unavailable</dd></dl> : <EmptyState title="Analysis pending" />}</section>
        <section><span className="eyebrow">PUBLIC METRICS</span><div className="mini-metrics"><span><b>{event.metrics.likes}</b> likes</span><span><b>{event.metrics.shares}</b> shares</span><span><b>{event.metrics.comments}</b> replies</span><span><b>{event.metrics.views}</b> views</span></div></section>
      </aside>
    </div>
  )
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label className="feed-filter"><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option} value={option}>{sentenceCase(option)}</option>)}</select></label>
}
