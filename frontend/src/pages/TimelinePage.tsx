import { Activity, BrainCircuit, GitBranch, TrendingDown, TrendingUp } from 'lucide-react'
import { useMemo } from 'react'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { PlatformBadge } from '../components/PlatformBadge'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useTimelineData } from '../hooks/useApiQueries'
import { formatDateTime } from '../utils/format'

interface TimelineItem { id: string; timestamp: string; lane: string; title: string; detail: string; status?: string; platform?: string }

export function TimelinePage() {
  const [events, sentiment, trends, network, graph] = useTimelineData()
  const error = [events, sentiment, trends, network, graph].find((query) => query.error)?.error
  const items = useMemo<TimelineItem[]>(() => {
    const eventItems = (events.data?.items ?? []).slice(0, 20).map(({ event, analysis }) => ({ id: event.event_id, timestamp: event.created_at, lane: 'Event', title: event.content.text, detail: analysis ? `${analysis.sentiment.label} · ${analysis.emotions.primary_label ?? 'emotion unavailable'}` : 'Analysis pending', platform: event.platform }))
    const topics = (trends.data?.items ?? []).filter((topic) => topic.window_end).map((topic) => ({ id: `topic-${topic.topic_id}`, timestamp: topic.window_end!, lane: 'Topic', title: topic.topic, detail: `Volume ${topic.volume}${topic.velocity == null ? ' · velocity unavailable' : ` · velocity ${topic.velocity.toFixed(2)}`}`, status: topic.status }))
    const shifts = (sentiment.data?.rolling_1h ?? []).slice(-8).map((point) => ({ id: `sentiment-${point.window_end}`, timestamp: point.window_end, lane: 'Sentiment', title: `${Math.round(point.positive_ratio * 100)}% positive · ${Math.round(point.negative_ratio * 100)}% negative`, detail: `${point.event_count} events in rolling window` }))
    const emotions = (sentiment.data?.rolling_1h ?? []).slice(-8).map((point) => ({ id: `emotion-${point.window_end}`, timestamp: point.window_end, lane: 'Emotion', title: `${Math.round(point.excitement_average * 100)}% excitement · ${Math.round(point.anxiety_average * 100)}% anxiety`, detail: `Model distribution across ${point.event_count} events` }))
    const interactions = (graph.data?.edges ?? []).slice(0, 12).map((edge) => ({ id: `edge-${edge.event_id}-${edge.source}-${edge.target}`, timestamp: edge.occurred_at, lane: 'Network', title: `${edge.source} → ${edge.target}`, detail: `${edge.interaction_type} relationship · configured weight ${edge.weight}` }))
    return [...eventItems, ...topics, ...shifts, ...emotions, ...interactions].sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime())
  }, [events.data, sentiment.data, trends.data, graph.data])
  if (events.isLoading || trends.isLoading) return <LoadingState />
  if (error) return <ErrorState error={error} />
  return (
    <div className="page-stack"><PageHeader title="Timeline" subtitle="A chronological intelligence view using event and analytical source timestamps." />
      <div className="timeline-summary"><span><Activity size={16} /> {events.data?.items.length ?? 0} recent events</span><span><BrainCircuit size={16} /> {sentiment.data?.rolling_1h.length ?? 0} sentiment windows</span><span><GitBranch size={16} /> {network.data?.summary.edges ?? 0} interactions</span></div>
      <Panel title="Intelligence Timeline" subtitle="Events, topics, model measurements and interaction edges"><div className="timeline">{items.length ? items.map((item) => <article key={item.id} className="timeline-item"><time>{formatDateTime(item.timestamp)}</time><div className={`timeline-item__marker timeline-item__marker--${item.lane.toLowerCase()}`}>{item.status === 'cooling' ? <TrendingDown size={14} /> : item.status === 'rising' ? <TrendingUp size={14} /> : <Activity size={14} />}</div><div><span className="eyebrow">{item.lane}</span><h3>{item.title}</h3><p>{item.detail}</p><div>{item.platform && <PlatformBadge platform={item.platform} />}{item.status && <StatusBadge status={item.status} />}</div></div></article>) : <EmptyState />}</div></Panel>
    </div>
  )
}
