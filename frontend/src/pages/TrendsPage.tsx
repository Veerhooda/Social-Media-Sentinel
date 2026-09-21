import { ArrowUpRight, Gauge, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useTopics, useTrends } from '../hooks/useApiQueries'
import { formatDateTime, formatNumber, sentenceCase } from '../utils/format'

export function TrendsPage() {
  const trends = useTrends()
  const topics = useTopics()
  const [search, setSearch] = useState('')
  const items = useMemo(() => (topics.data?.items ?? []).filter((topic) => `${topic.topic} ${topic.keywords.join(' ')}`.toLowerCase().includes(search.toLowerCase())), [topics.data, search])
  if (trends.isLoading || topics.isLoading) return <LoadingState label="Loading BERTrend measurements…" />
  if (trends.error || topics.error) return <ErrorState error={trends.error ?? topics.error} />
  return (
    <div className="page-stack">
      <PageHeader title="Trends & Topics" subtitle="BERTrend topic discovery, chronological measurements and evidence-backed status." actions={<StatusBadge status={trends.data?.temporal_status ?? 'INSUFFICIENT_DATA'} />} />
      {trends.data?.detail && <div className="insight-callout"><Gauge size={18} /><span>{trends.data.detail}</span></div>}
      <Panel title="Topic Ranking" subtitle={`Engine: ${trends.data?.engine ?? 'Unavailable'} · fallback ${trends.data?.fallback ? 'active' : 'inactive'}`}>
        <div className="table-toolbar"><label><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search topics or keywords" /></label><span>{items.length} topics</span></div>
        {items.length ? <div className="data-table"><div className="data-table__header trends-columns"><span>Topic</span><span>Volume</span><span>Growth</span><span>Velocity</span><span>Window</span><span>Status</span><span /></div>{items.map((topic) => <div className="data-table__row trends-columns" key={topic.topic_id ?? topic.topic}><div><strong>{topic.topic}</strong><span>{topic.keywords.slice(0, 4).join(' · ') || 'No keywords'}</span></div><b>{formatNumber(topic.volume)}</b><span>{topic.growth == null ? 'Insufficient' : `${topic.growth >= 0 ? '+' : ''}${(topic.growth * 100).toFixed(1)}%`}</span><span>{topic.velocity == null ? '—' : topic.velocity.toFixed(2)}</span><time>{formatDateTime(topic.window_end)}</time><StatusBadge status={topic.status} />{topic.topic_id ? <Link to={`/trends/${topic.topic_id}`} aria-label={`Open ${topic.topic}`}><ArrowUpRight size={16} /></Link> : <span />}</div>)}</div> : <EmptyState title="No topic evidence" detail="BERTrend has not persisted a topic for the selected corpus." />}
      </Panel>
      <div className="dashboard-grid">
        <Panel title="Status Semantics" subtitle="React never infers a trend status" className="span-6"><div className="insight-list"><p><b>Emerging</b><span>First observed measurement.</span></p><p><b>Rising / Cooling</b><span>Requires a prior matched measurement and backend velocity.</span></p><p><b>Acceleration</b><span>Requires at least three matched measurements.</span></p></div></Panel>
        <Panel title="Temporal Evidence" subtitle="Latest backend assessment" className="span-6"><div className="big-status"><StatusBadge status={trends.data?.temporal_status ?? 'INSUFFICIENT_DATA'} /><strong>{sentenceCase(trends.data?.temporal_status ?? 'INSUFFICIENT_DATA')}</strong><p>{trends.data?.temporal_status === 'PASS' ? 'At least one topic has comparable chronological measurements.' : 'More matched source-time measurements are required.'}</p></div></Panel>
      </div>
    </div>
  )
}

