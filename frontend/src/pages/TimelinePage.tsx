import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Platform } from '../components/Platform'
import { Segmented } from '../components/Segmented'
import { Status } from '../components/Status'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { useTimelineData } from '../hooks/useApiQueries'
import { topicState } from '../utils/dashboard'
import { formatDate, pct } from '../utils/format'
import { shortNodeLabel } from '../utils/network'

type Lane = 'all' | 'event' | 'topic' | 'sentiment' | 'link'
interface Item { id: string; at: string; lane: Exclude<Lane, 'all'>; title: string; detail: string; platform?: string; status?: { status: string; label: string }; to?: string; sentiment?: string }

const LANES: { value: Lane; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'event', label: 'Posts' },
  { value: 'topic', label: 'Topics' },
  { value: 'sentiment', label: 'Sentiment' },
  { value: 'link', label: 'Links' },
]

export function TimelinePage() {
  const [events, sentiment, trends, , graph] = useTimelineData()
  const [lane, setLane] = useState<Lane>('all')
  const items = useMemo<Item[]>(() => {
    const posts: Item[] = (events.data?.items ?? []).slice(0, 40).map(({ event, analysis }) => ({
      id: event.event_id, at: event.created_at, lane: 'event', title: event.content.text || '(no text)',
      detail: `${event.author.username ? `@${event.author.username}` : event.author.display_name ?? 'unknown'} · ${event.interaction_type}`,
      platform: event.platform, sentiment: analysis?.sentiment.label, to: `/live-feed?event=${event.event_id}`,
    }))
    const topics: Item[] = (trends.data?.items ?? []).filter((topic) => topic.window_end).map((topic) => ({
      id: `topic-${topic.topic_id ?? topic.topic}`, at: topic.window_end!, lane: 'topic', title: topic.topic,
      detail: `${topic.volume} documents${topic.velocity != null ? ` · ${topic.velocity.toFixed(2)}/h` : ''}`, status: topicState(topic), to: topic.topic_id ? `/trends/${topic.topic_id}` : undefined,
    }))
    const windows: Item[] = (sentiment.data?.daily ?? []).slice(-14).map((point) => ({
      id: `sentiment-${point.window_end}`, at: point.window_start, lane: 'sentiment',
      title: `${pct(point.positive_ratio, 0)} positive, ${pct(point.negative_ratio, 0)} negative`,
      detail: `${point.event_count} analysed events that day · irony ${pct(point.irony_rate, 0)}`, to: '/sentiment',
    }))
    // One event can create several edges between the same accounts (e.g. reply + mention): show it once.
    const byLink = new Map<string, Item>()
    for (const edge of graph.data?.edges ?? []) {
      const id = `link-${edge.event_id}-${edge.source}-${edge.target}`
      const existing = byLink.get(id)
      if (existing) {
        if (!existing.detail.split(', ').includes(edge.interaction_type)) existing.detail += `, ${edge.interaction_type}`
        continue
      }
      if (byLink.size >= 30) continue
      byLink.set(id, {
        id, at: edge.occurred_at, lane: 'link',
        title: `${shortNodeLabel(edge.source)} → ${shortNodeLabel(edge.target)}`, detail: edge.interaction_type, platform: edge.source.split(':')[0], to: '/network',
      })
    }
    const links = [...byLink.values()]
    return [...posts, ...topics, ...windows, ...links].sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
  }, [events.data, sentiment.data, trends.data, graph.data])

  const error = [events, sentiment, trends, graph].find((query) => query.error)?.error
  if (events.isLoading || trends.isLoading) return <div className="page"><LoadingState label="Loading timeline" /></div>
  if (error) return <div className="page"><ErrorState error={error} /></div>

  const shown = lane === 'all' ? items : items.filter((item) => item.lane === lane)
  const groups = shown.reduce<{ day: string; items: Item[] }[]>((acc, item) => {
    const day = formatDate(item.at)
    const group = acc.at(-1)
    if (group?.day === day) group.items.push(item)
    else acc.push({ day, items: [item] })
    return acc
  }, [])

  return (
    <div className="page">
      <PageHeader title="Timeline" description="Recent posts, topic windows, daily sentiment and new links in source-time order" actions={<Segmented label="Show" value={lane} options={LANES} onChange={setLane} />} />
      {groups.length ? groups.map((group) => (
        <Panel key={group.day} title={group.day} description={`${group.items.length} ${group.items.length === 1 ? 'entry' : 'entries'}`} flush>
          <div className="rows">
            {group.items.map((item) => {
              const body = (
                <>
                  <span className="faint num" style={{ fontSize: 12, width: 44 }}>{item.lane === 'sentiment' ? 'Day' : new Date(item.at).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', hour12: false })}</span>
                  <div style={{ minWidth: 0 }}>
                    <div className="row__title clamp-2" style={{ fontWeight: item.lane === 'event' ? 400 : 550 }}>{item.title}</div>
                    <div className="row__meta">
                      <span>{LANES.find((entry) => entry.value === item.lane)?.label.replace(/s$/, '')}</span>
                      {item.platform && <Platform platform={item.platform} />}
                      {item.sentiment && <span className="sentiment"><i className={`dot dot--${item.sentiment}`} />{item.sentiment}</span>}
                      {item.status && <Status status={item.status.status} label={item.status.label} />}
                      <span>{item.detail}</span>
                    </div>
                  </div>
                </>
              )
              return item.to
                ? <Link key={item.id} to={item.to} className="row" style={{ gridTemplateColumns: '48px minmax(0,1fr)' }}>{body}</Link>
                : <div key={item.id} className="row" style={{ gridTemplateColumns: '48px minmax(0,1fr)' }}>{body}</div>
            })}
          </div>
        </Panel>
      )) : <Panel><EmptyState title="Nothing to show" /></Panel>}
    </div>
  )
}
