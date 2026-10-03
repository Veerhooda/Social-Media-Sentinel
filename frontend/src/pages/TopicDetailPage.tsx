import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getTopic, getTopicEvolution } from '../api/analytics'
import { TopicEvolutionChart } from '../charts/TopicEvolutionChart'
import { SENTIMENT_COLORS } from '../charts/theme'
import { StackBar } from '../components/Bars'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Stat, Stats } from '../components/Stat'
import { Status } from '../components/Status'
import { ErrorState, LoadingState } from '../components/States'
import { topicState } from '../utils/dashboard'
import { formatDateTime, formatNumber } from '../utils/format'

export function TopicDetailPage() {
  const topicId = Number(useParams().topicId)
  const topic = useQuery({ queryKey: ['topic', topicId], queryFn: () => getTopic(topicId), enabled: Number.isFinite(topicId) })
  const evolution = useQuery({ queryKey: ['topic', topicId, 'evolution'], queryFn: () => getTopicEvolution(topicId), enabled: Number.isFinite(topicId) })
  if (topic.isLoading || evolution.isLoading) return <div className="page"><LoadingState label="Loading topic" /></div>
  if (topic.error || evolution.error || !topic.data) return <div className="page"><ErrorState error={topic.error ?? evolution.error} /></div>
  const data = topic.data
  const state = topicState(data)
  const sentiment = Object.entries(data.sentiment)
  return (
    <div className="page">
      <Link to="/trends" className="back-link"><ArrowLeft size={14} /> Topics</Link>
      <PageHeader title={data.topic} description={data.keywords.join(', ')} actions={<Status status={state.status} label={state.label} />} />
      <Stats label="Topic measures">
        <Stat label="Volume" value={data.volume} meta="documents, latest window" />
        <Stat label="Growth" value={data.growth == null ? null : data.growth * 100} format={(n) => `${n >= 0 ? '+' : ''}${n.toFixed(0)}`} unit="%" meta="vs previous window" />
        <Stat label="Velocity" value={data.velocity} format={(n) => n.toFixed(2)} meta="documents per hour" />
        <Stat label="Acceleration" value={data.acceleration} format={(n) => n.toFixed(2)} meta="needs three windows" />
        <Stat label="Windows" value={data.evolution.length} meta={`${data.model_name ?? data.source}`} />
      </Stats>
      <Panel title="Volume over time" description={evolution.data?.detail ?? 'Documents per measured window'}>
        <TopicEvolutionChart points={evolution.data?.items ?? data.evolution} />
      </Panel>
      <div className="grid">
        <Panel className="col-6" title="Sentiment in this topic">
          {sentiment.length ? (
            <div style={{ display: 'grid', gap: 10 }}>
              <StackBar label="Topic sentiment" parts={sentiment.map(([key, value]) => ({ key, value, label: key, color: SENTIMENT_COLORS[key] ?? 'var(--neu)' }))} />
              <div className="legend">{sentiment.map(([key, value]) => <span key={key}><i className={`dot dot--${key}`} />{key} {formatNumber(value)}</span>)}</div>
            </div>
          ) : <p className="muted">No sentiment attached to this topic.</p>}
        </Panel>
        <Panel className="col-6" title="Observed">
          <dl className="kv">
            <dt>First seen</dt><dd>{formatDateTime(data.first_seen_at)}</dd>
            <dt>Last seen</dt><dd>{formatDateTime(data.last_seen_at)}</dd>
            <dt>Latest window</dt><dd>{formatDateTime(data.window_start)} – {formatDateTime(data.window_end)}</dd>
          </dl>
        </Panel>
      </div>
    </div>
  )
}
