import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, ExternalLink, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getEnrichedEvent } from '../api/events'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Platform } from '../components/Platform'
import { platformLabel } from '../utils/platform'
import { Status } from '../components/Status'
import { EmptyState, ErrorState, LoadingState, Notice } from '../components/States'
import { useEmotions, useEnrichedEvents, useSystem } from '../hooks/useApiQueries'
import type { EnrichedEvent } from '../types/events'
import { formatDateTime, formatNumber, formatShortTime, sentenceCase } from '../utils/format'

const PAGE = 50
/** Canonical interaction types (app/models/events.py InteractionType). */
const INTERACTIONS = ['post', 'comment', 'reply', 'mention', 'quote', 'repost', 'forward']
const SENTIMENTS = ['positive', 'neutral', 'negative']

interface Filters { search: string; platform: string; sentiment: string; emotion: string; interaction: string }
const EMPTY: Filters = { search: '', platform: '', sentiment: '', emotion: '', interaction: '' }

export function LiveFeedPage() {
  const [params, setParams] = useSearchParams()
  const [filters, setFilters] = useState<Filters>({ ...EMPTY, search: params.get('q') ?? '' })
  const [debounced, setDebounced] = useState(filters.search)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<EnrichedEvent | null>(null)
  const [health] = useSystem()
  const emotions = useEmotions()
  const seen = useRef<Set<string> | null>(null)

  useEffect(() => { const q = params.get('q') ?? ''; setFilters((current) => (current.search === q ? current : { ...current, search: q })) }, [params])
  useEffect(() => {
    const timer = window.setTimeout(() => { setDebounced(filters.search.trim()); setOffset(0) }, 300)
    return () => window.clearTimeout(timer)
  }, [filters.search])

  const query = useMemo(() => ({
    offset,
    q: debounced || undefined,
    platform: filters.platform || undefined,
    sentiment: filters.sentiment || undefined,
    emotion: filters.emotion || undefined,
    interaction: filters.interaction || undefined,
  }), [offset, debounced, filters.platform, filters.sentiment, filters.emotion, filters.interaction])
  const events = useEnrichedEvents(query)

  // Deep link from other pages: /live-feed?event=<id>
  const eventId = params.get('event')
  const linked = useQuery({
    queryKey: ['events', 'enriched', 'one', eventId],
    queryFn: () => getEnrichedEvent(eventId!),
    retry: false,
    enabled: Boolean(eventId),
  })
  useEffect(() => { if (linked.data) setSelected(linked.data) }, [linked.data])

  // Highlight rows that arrive while the page is open.
  const items = events.data?.items ?? []
  const fresh = new Set<string>()
  if (seen.current) items.forEach((item) => { if (!seen.current!.has(item.event.event_id)) fresh.add(item.event.event_id) })
  useEffect(() => { if (events.data) seen.current = new Set(events.data.items.map((item) => item.event.event_id)) }, [events.data])
  useEffect(() => { seen.current = null }, [query])

  const platforms = (health.data?.platforms ?? []).filter((platform) => platform.event_count > 0).map((platform) => platform.platform)
  const emotionOptions = useMemo(() => {
    const latest = emotions.data?.daily.at(-1)?.emotion_distribution ?? {}
    return Object.keys(latest).filter((label) => label !== 'nervousness').sort()
  }, [emotions.data])
  const active = Object.entries(filters).some(([key, value]) => key !== 'search' ? Boolean(value) : Boolean(value.trim()))
  const updating = debounced !== filters.search.trim() || events.isPlaceholderData
  const total = events.data?.total ?? 0
  const set = (patch: Partial<Filters>) => { setOffset(0); setFilters((current) => ({ ...current, ...patch })) }
  const close = () => { setSelected(null); if (eventId) { params.delete('event'); setParams(params, { replace: true }) } }

  return (
    <div className="page">
      <PageHeader
        title="Conversations"
        description="Every collected post, comment and reply with its model analysis. Refreshes every 5 seconds."
        actions={<Status status="running" label={`${formatNumber(total)} ${active ? 'matching' : 'events'}`} />}
      />
      {linked.error && <Notice tone="error">The linked conversation could not be loaded: {linked.error instanceof Error ? linked.error.message : 'unknown error'}</Notice>}
      <Panel
        flush
        title={
          <div className="filters" role="search">
            <input className="input" style={{ width: 260 }} value={filters.search} maxLength={200} placeholder="Search text, author or hashtag" aria-label="Search conversations" onChange={(event) => set({ search: event.target.value })} />
            <FilterSelect label="Platform" value={filters.platform} options={platforms} format={platformLabel} onChange={(platform) => set({ platform })} />
            <FilterSelect label="Sentiment" value={filters.sentiment} options={SENTIMENTS} onChange={(sentiment) => set({ sentiment })} />
            <FilterSelect label="Emotion" value={filters.emotion} options={emotionOptions} onChange={(emotion) => set({ emotion })} />
            <FilterSelect label="Type" value={filters.interaction} options={INTERACTIONS} onChange={(interaction) => set({ interaction })} />
            {active && <button type="button" className="btn btn--ghost btn--sm" onClick={() => { setFilters(EMPTY); setOffset(0); setParams({}) }}><X size={13} /> Clear</button>}
            {updating && <span className="spinner" aria-label="Updating results" />}
          </div>
        }
        footer={
          <>
            <span className="num">{total ? `${offset + 1}–${Math.min(offset + PAGE, total)} of ${formatNumber(total)}` : 'No results'}</span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button type="button" className="btn btn--sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}><ChevronLeft size={14} /> Newer</button>
              <button type="button" className="btn btn--sm" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Older <ChevronRight size={14} /></button>
            </div>
          </>
        }
      >
        <div aria-live="polite" className="sr-only">{updating ? 'Updating results' : `${total} events`}</div>
        {events.isLoading ? <div className="panel__body"><LoadingState label="Loading conversations" /></div>
          : events.error ? <div className="panel__body"><ErrorState error={events.error} /></div>
          : items.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th style={{ width: 132 }}>Time</th><th style={{ width: 200 }}>Source</th><th>Text</th><th style={{ width: 170 }}>Analysis</th><th className="r" style={{ width: 96 }}>Reach</th></tr></thead>
                <tbody>
                  {items.map((item) => <EventRow key={item.event.event_id} item={item} fresh={fresh.has(item.event.event_id)} onOpen={() => setSelected(item)} />)}
                </tbody>
              </table>
            </div>
          ) : <div className="panel__body"><EmptyState title="Nothing matches these filters" detail="Clear a filter or try another search." /></div>}
      </Panel>
      {selected && <EventDrawer item={selected} onClose={close} />}
    </div>
  )
}

function FilterSelect({ label, value, options, onChange, format = sentenceCase }: { label: string; value: string; options: string[]; onChange: (value: string) => void; format?: (value: string) => string }) {
  return (
    <select className="select" style={{ width: 'auto', minWidth: 120 }} aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">{label}: all</option>
      {options.map((option) => <option key={option} value={option}>{format(option)}</option>)}
    </select>
  )
}

function reach(item: EnrichedEvent) {
  const metrics = item.event.metrics
  if (metrics.views) return `${formatNumber(metrics.views)} views`
  const engagement = metrics.likes + metrics.shares + metrics.comments
  return engagement ? `${formatNumber(engagement)} interactions` : '–'
}

function EventRow({ item, fresh, onOpen }: { item: EnrichedEvent; fresh: boolean; onOpen: () => void }) {
  const { event, analysis } = item
  return (
    <tr className={`is-clickable ${fresh ? 'is-new' : ''}`} tabIndex={0} onClick={onOpen} onKeyDown={(keyEvent) => { if (keyEvent.key === 'Enter' || keyEvent.key === ' ') { keyEvent.preventDefault(); onOpen() } }} aria-label={`Open ${event.interaction_type} from ${event.author.username ?? 'unknown author'}`}>
      <td className="num" style={{ whiteSpace: 'nowrap' }}>{formatShortTime(event.created_at)}</td>
      <td>
        <Platform platform={event.platform} />
        <div className="faint truncate" style={{ maxWidth: 180, fontSize: 12 }}>{event.author.username ? `@${event.author.username}` : event.author.display_name ?? 'Unknown author'} · {event.interaction_type}</div>
      </td>
      <td><p className="clamp-2" style={{ color: 'var(--text)' }}>{event.content.text || '(no text)'}</p></td>
      <td>
        {analysis ? (
          <div style={{ display: 'grid', gap: 2 }}>
            <span className="sentiment"><i className={`dot dot--${analysis.sentiment.label}`} />{analysis.sentiment.label}</span>
            <span className="faint" style={{ fontSize: 12 }}>{sentenceCase(analysis.emotions.primary_label ?? 'no emotion')}{analysis.irony.is_ironic ? ' · ironic' : ''}</span>
          </div>
        ) : <Status status="pending" label="Not analysed yet" />}
      </td>
      <td className="r faint">{reach(item)}</td>
    </tr>
  )
}

function sourceLink(item: EnrichedEvent) {
  const { event } = item
  const meta = event.source_metadata as Record<string, unknown>
  if (event.platform === 'x' && /^\d+$/.test(event.platform_post_id)) return `https://x.com/i/web/status/${event.platform_post_id}`
  if (event.platform === 'telegram' && typeof meta.channel_username === 'string' && meta.message_id) return `https://t.me/${meta.channel_username}/${meta.message_id}`
  if (event.platform === 'youtube' && typeof meta.video_id === 'string') return `https://www.youtube.com/watch?v=${meta.video_id}`
  return null
}

function EventDrawer({ item, onClose }: { item: EnrichedEvent; onClose: () => void }) {
  const { event, analysis } = item
  const dialog = useRef<HTMLElement>(null)
  const onCloseRef = useRef(onClose)
  useEffect(() => { onCloseRef.current = onClose }, [onClose])
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const onKey = (keyEvent: KeyboardEvent) => {
      if (keyEvent.key === 'Escape') { keyEvent.preventDefault(); onCloseRef.current() }
      if (keyEvent.key !== 'Tab') return
      const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? [])
      if (!controls.length) return
      const first = controls[0]
      const last = controls.at(-1)!
      if (keyEvent.shiftKey && document.activeElement === first) { keyEvent.preventDefault(); last.focus() }
      else if (!keyEvent.shiftKey && document.activeElement === last) { keyEvent.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); previous?.focus() }
  }, [])
  const link = sourceLink(item)
  const scores = analysis ? Object.entries(analysis.sentiment.scores).sort((a, b) => b[1] - a[1]) : []
  const topEmotions = analysis ? Object.entries(analysis.emotions.scores).filter(([label]) => label !== 'nervousness').sort((a, b) => b[1] - a[1]).slice(0, 4) : []
  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside ref={dialog} className="drawer" role="dialog" aria-modal="true" aria-label="Event details" onClick={(clickEvent) => clickEvent.stopPropagation()}>
        <header><h2><Platform platform={event.platform} /></h2><button type="button" className="btn btn--ghost btn--icon" onClick={onClose} aria-label="Close event details"><X size={16} /></button></header>
        <section>
          <p className="drawer__text">{event.content.text || '(no text)'}</p>
          {link && <a className="link" href={link} target="_blank" rel="noopener noreferrer">Open on {platformLabel(event.platform)} <ExternalLink size={12} style={{ display: 'inline', verticalAlign: '-1px' }} /></a>}
        </section>
        <section>
          <h3>Source</h3>
          <dl className="kv">
            <dt>Author</dt><dd>{event.author.display_name ?? event.author.username ?? event.author.platform_user_id}{event.author.username ? ` (@${event.author.username})` : ''}</dd>
            <dt>Type</dt><dd>{sentenceCase(event.interaction_type)}</dd>
            <dt>Posted</dt><dd>{formatDateTime(event.created_at)}</dd>
            <dt>Collected</dt><dd>{formatDateTime(event.collected_at)}</dd>
            <dt>Post ID</dt><dd className="mono">{event.platform_post_id}</dd>
            {event.source_metadata.replay === true && <><dt>Data</dt><dd>Replay fixture</dd></>}
          </dl>
        </section>
        <section>
          <h3>Analysis</h3>
          {analysis ? (
            <dl className="kv">
              <dt>Sentiment</dt><dd>{scores.map(([label, score]) => `${label} ${Math.round(score * 100)}%`).join(' · ')}</dd>
              <dt>Emotions</dt><dd>{topEmotions.map(([label, score]) => `${label === 'anxiety' ? 'anxiety (nervousness)' : label} ${Math.round(score * 100)}%`).join(' · ') || '–'}</dd>
              <dt>Irony</dt><dd>{analysis.irony.is_ironic ? 'Ironic' : 'Not ironic'} · {Math.round(analysis.irony.confidence * 100)}% confidence</dd>
              <dt>Stance</dt><dd>{analysis.stance.supported && analysis.stance.label ? `${analysis.stance.label} on ${analysis.stance.target}` : 'No validated target'}</dd>
              <dt>Models</dt><dd className="faint" style={{ fontSize: 12 }}>{[analysis.sentiment.model_name, analysis.emotions.model_name, analysis.irony.model_name].join(', ')}</dd>
            </dl>
          ) : <p className="muted">Waiting for the NLP job.</p>}
        </section>
        <section>
          <h3>Public metrics</h3>
          <dl className="kv">
            {(['views', 'likes', 'shares', 'comments', 'quotes'] as const).map((key) => <div key={key} style={{ display: 'contents' }}><dt>{sentenceCase(key)}</dt><dd className="num">{formatNumber(event.metrics[key])}</dd></div>)}
          </dl>
        </section>
      </aside>
    </div>
  )
}
