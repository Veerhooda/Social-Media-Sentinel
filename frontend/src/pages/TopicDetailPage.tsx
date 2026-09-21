import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BrainCircuit, Clock3, Gauge } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getTopic, getTopicEvolution } from '../api/analytics'
import { TopicEvolutionChart } from '../charts/TopicEvolutionChart'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { formatDateTime, formatNumber } from '../utils/format'

export function TopicDetailPage() {
  const topicId = Number(useParams().topicId)
  const topic = useQuery({ queryKey: ['topic', topicId], queryFn: () => getTopic(topicId), enabled: Number.isFinite(topicId) })
  const evolution = useQuery({ queryKey: ['topic', topicId, 'evolution'], queryFn: () => getTopicEvolution(topicId), enabled: Number.isFinite(topicId) })
  if (topic.isLoading || evolution.isLoading) return <LoadingState />
  if (topic.error || evolution.error) return <ErrorState error={topic.error ?? evolution.error} />
  const data = topic.data!
  return (
    <div className="page-stack">
      <Link to="/trends" className="back-link"><ArrowLeft size={15} /> All topics</Link>
      <PageHeader title={data.topic} subtitle={`Model: ${data.model_name ?? data.source}`} actions={<StatusBadge status={data.status} />} />
      <div className="metric-grid metric-grid--four"><MetricCard label="Current Volume" value={formatNumber(data.volume)} detail="documents in latest window" icon={Gauge} /><MetricCard label="Velocity" value={data.velocity == null ? 'Unavailable' : data.velocity.toFixed(2)} detail="documents per elapsed hour" icon={Clock3} tone="blue" unavailable={data.velocity == null} /><MetricCard label="Growth" value={data.growth == null ? 'Unavailable' : `${(data.growth * 100).toFixed(1)}%`} detail="vs prior matched measurement" icon={Gauge} tone="green" unavailable={data.growth == null} /><MetricCard label="Sentiment Coverage" value={Object.keys(data.sentiment).length} detail="labels associated with topic" icon={BrainCircuit} tone="purple" /></div>
      <Panel title="Topic Evolution" subtitle={evolution.data?.detail ?? 'Chronological source-time volume'} action={<StatusBadge status={evolution.data?.status ?? 'INSUFFICIENT_DATA'} />}><TopicEvolutionChart points={evolution.data?.items ?? []} /></Panel>
      <div className="dashboard-grid"><Panel title="Keywords" subtitle="BERTrend representation" className="span-6"><div className="keyword-cloud">{data.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}</div></Panel><Panel title="Observation Window" subtitle="Persisted source-time bounds" className="span-6"><dl className="detail-list"><dt>First seen</dt><dd>{formatDateTime(data.first_seen_at)}</dd><dt>Last seen</dt><dd>{formatDateTime(data.last_seen_at)}</dd><dt>Measurements</dt><dd>{data.evolution.length}</dd><dt>Acceleration</dt><dd>{data.acceleration == null ? 'Insufficient data' : data.acceleration.toFixed(2)}</dd></dl></Panel></div>
    </div>
  )
}

