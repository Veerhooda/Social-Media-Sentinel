import { ChevronLeft, ChevronRight, Filter, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { PlatformBadge } from '../components/PlatformBadge'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useEnrichedEvents } from '../hooks/useApiQueries'
import type { EnrichedEvent } from '../types/events'
import { filterEnrichedEvents, type EventFilters } from '../utils/dashboard'
import { formatDateTime, formatNumber, sentenceCase } from '../utils/format'

export function LiveFeedPage() {
  const [params] = useSearchParams()
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<EnrichedEvent | null>(null)
  const [filters, setFilters] = useState<EventFilters>({
    search: params.get('q') ?? '', platform: 'all', sentiment: 'all', emotion: 'all', interaction: 'all',
  })
  const events = useEnrichedEvents(offset, filters.platform)
  const filtered = useMemo(() => filterEnrichedEvents(events.data?.items ?? [], filters), [events.data, filters])
  const hasReal = events.data?.items.some(({ event }) => !event.source_metadata.replay)
  const hasReplay = events.data?.items.some(({ event }) => Boolean(event.source_metadata.replay))
  const mode = hasReal && hasReplay ? 'mixed' : hasReal ? 'live' : hasReplay ? 'replay' : 'idle'
  if (events.isLoading) return <LoadingState label="Loading chronological event feed…" />
  if (events.error) return <ErrorState error={events.error} />
  return (
    <div className="page-stack">
      <PageHeader title="Live Feed" subtitle="Chronological canonical events with persisted NLP analysis." actions={<StatusBadge status={mode} label={mode === 'live' ? 'REAL DATA' : mode === 'mixed' ? 'MIXED DATA' : undefined} />} />
      <Panel className="feed-panel" title="Event Stream" subtitle={`${events.data?.total ?? 0} stored events · refreshed every 5 seconds`} action={<Filter size={17} aria-hidden="true" />}>
        <div className="filter-bar">
          <input value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="Search text, author or hashtag" aria-label="Search event feed" />
          <Select label="Platform" value={filters.platform} onChange={(value) => { setOffset(0); setFilters({ ...filters, platform: value }) }} options={['all', 'x', 'telegram']} />
          <Select label="Sentiment" value={filters.sentiment} onChange={(value) => setFilters({ ...filters, sentiment: value })} options={['all', 'positive', 'neutral', 'negative']} />
          <Select label="Emotion" value={filters.emotion} onChange={(value) => setFilters({ ...filters, emotion: value })} options={['all', 'excitement', 'approval', 'neutral', 'admiration', 'anxiety']} />
          <Select label="Interaction" value={filters.interaction} onChange={(value) => setFilters({ ...filters, interaction: value })} options={['all', 'post', 'mention', 'reply', 'quote', 'repost', 'forward']} />
          <select disabled aria-label="Topic filter unavailable"><option>Topic assignment unavailable</option></select>
        </div>
        {filtered.length ? (
          <div className="event-table" role="table" aria-label="Canonical event feed">
            <div className="event-table__header" role="row"><span>Time</span><span>Source</span><span>Conversation</span><span>Analysis</span><span>Metrics</span></div>
            {filtered.map((item) => <EventRow key={item.event.event_id} item={item} onClick={() => setSelected(item)} />)}
          </div>
        ) : <EmptyState title="No events match these filters" detail="Clear filters or wait for the next backend poll." />}
        <div className="pagination">
          <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}><ChevronLeft size={15} /> Newer</button>
          <span>{offset + 1}–{Math.min(offset + 50, events.data?.total ?? 0)} of {events.data?.total ?? 0}</span>
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
      <time>{formatDateTime(event.created_at)}</time>
      <div><PlatformBadge platform={event.platform} /><span>{event.author.username ? `@${event.author.username}` : event.author.display_name ?? 'Unknown author'}</span></div>
      <div className="event-row__content"><strong>{sentenceCase(event.interaction_type)} · Topic unavailable</strong><p>{event.content.text}</p></div>
      <div>{analysis ? <><StatusBadge status={analysis.sentiment.label} /><span>{sentenceCase(analysis.emotions.primary_label ?? 'Unknown emotion')}</span>{analysis.irony.is_ironic && <em>Irony {Math.round(analysis.irony.confidence * 100)}%</em>}</> : <StatusBadge status="pending" label="Analysis pending" />}</div>
      <b>{activity}</b>
    </button>
  )
}

function EventDrawer({ item, onClose }: { item: EnrichedEvent; onClose: () => void }) {
  const { event, analysis } = item
  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside className="event-drawer" role="dialog" aria-modal="true" aria-label="Event details" onClick={(event) => event.stopPropagation()}>
        <header><div><PlatformBadge platform={item.event.platform} /><h2>Event Detail</h2></div><button type="button" onClick={onClose} aria-label="Close event detail"><X size={19} /></button></header>
        <section><span className="eyebrow">SOURCE EVENT</span><p className="drawer-text">{event.content.text}</p><dl><dt>Created</dt><dd>{formatDateTime(event.created_at)}</dd><dt>Collected</dt><dd>{formatDateTime(event.collected_at)}</dd><dt>Type</dt><dd>{event.interaction_type}</dd><dt>Source ID</dt><dd>{event.platform_post_id}</dd></dl></section>
        <section><span className="eyebrow">NLP ANALYSIS</span>{analysis ? <dl><dt>Sentiment</dt><dd>{sentenceCase(analysis.sentiment.label)} · {Math.round(analysis.sentiment.confidence * 100)}%</dd><dt>Primary emotion</dt><dd>{sentenceCase(analysis.emotions.primary_label ?? 'Unavailable')}</dd><dt>Irony</dt><dd>{analysis.irony.is_ironic ? 'Detected' : 'Not detected'} · {Math.round(analysis.irony.confidence * 100)}%</dd><dt>Stance</dt><dd>{analysis.stance.supported ? analysis.stance.label : 'Unsupported for arbitrary target'}</dd><dt>Topic</dt><dd>Per-event assignment unavailable</dd></dl> : <EmptyState title="Analysis pending" />}</section>
        <section><span className="eyebrow">PUBLIC METRICS</span><div className="mini-metrics"><span><b>{event.metrics.likes}</b> likes</span><span><b>{event.metrics.shares}</b> shares</span><span><b>{event.metrics.comments}</b> replies</span><span><b>{event.metrics.views}</b> views</span></div></section>
      </aside>
    </div>
  )
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option} value={option}>{sentenceCase(option)}</option>)}</select>
}
