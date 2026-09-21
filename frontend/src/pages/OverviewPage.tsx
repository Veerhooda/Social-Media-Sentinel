import { Activity, GitBranch, MessageSquareText, RadioTower, TrendingUp, UsersRound } from 'lucide-react'
import { useState } from 'react'
import { ActivityHeatmap } from '../charts/ActivityHeatmap'
import { EmotionBars } from '../charts/EmotionBars'
import { SentimentChart } from '../charts/SentimentChart'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { PlatformBadge } from '../components/PlatformBadge'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { SystemStateStrip } from '../components/SystemStateStrip'
import { TimeRangeSelector, type TimeRange } from '../components/TimeRangeSelector'
import { useOverviewData } from '../hooks/useApiQueries'
import { NetworkGraph } from '../network/NetworkGraph'
import { activeUsers, emotionTotals, filterTemporalRange, sentimentShift } from '../utils/dashboard'
import { formatDateTime, formatNumber, formatPercent, sentenceCase } from '../utils/format'

export function OverviewPage() {
  const [range, setRange] = useState<TimeRange>('24H')
  const [health, jobs, events, enriched, sentiment, emotions, trends, network, graph] = useOverviewData()
  const essential = [health, events, sentiment, trends, network]
  const error = essential.find((query) => query.error)?.error
  if (essential.some((query) => query.isLoading)) return <LoadingState />
  if (error) return <ErrorState error={error} />

  const eventItems = events.data?.items ?? []
  const sentimentPoints = filterTemporalRange(sentiment.data?.rolling_1h ?? [], range)
  const emotionData = emotionTotals(filterTemporalRange(emotions.data?.rolling_1h ?? [], range))
  const topicItems = trends.data?.items ?? []
  const latestSentiment = sentimentPoints.at(-1)
  const hasReal = enriched.data?.items.some(({ event }) => !event.source_metadata.replay)
  const hasReplay = enriched.data?.items.some(({ event }) => Boolean(event.source_metadata.replay))
  const dataMode = hasReal && hasReplay ? 'mixed' : hasReal ? 'live' : 'replay'
  const platformSummary = (platform: string) => health.data?.platforms.find((item) => item.platform === platform)

  return (
    <div className="page-stack">
      <PageHeader
        title="Overview"
        subtitle="Current signals from the locally collected X and Telegram dataset."
        actions={<TimeRangeSelector value={range} onChange={setRange} />}
      />
      {health.data && <SystemStateStrip health={health.data} jobs={jobs.data} />}
      <div className="metric-grid">
        <MetricCard label="Collected Events" value={formatNumber(health.data?.real_event_count ?? 0)} detail="non-replay X + Telegram events" icon={RadioTower} tone="orange" />
        <MetricCard label="Active Users" value={formatNumber(activeUsers(eventItems))} detail="in loaded event window" icon={UsersRound} tone="blue" />
        <MetricCard label="Detected Topics" value={formatNumber(topicItems.length)} detail={trends.data?.temporal_status === 'PASS' ? 'BERTrend measurements' : 'limited temporal evidence'} icon={TrendingUp} tone="purple" />
        <MetricCard label="Sentiment Shift" value={formatPercent(sentimentShift(sentimentPoints))} detail="positive share vs prior window" change={sentimentShift(sentimentPoints)} icon={MessageSquareText} tone="green" unavailable={sentimentPoints.length < 2} />
        <MetricCard label="Network Activity" value={formatNumber(network.data?.summary.edges ?? 0)} detail="interaction-derived edges" icon={GitBranch} tone="pink" />
      </div>

      <div className="dashboard-grid dashboard-grid--primary">
        <Panel title="Sentiment Over Time" subtitle={`Source-time analysis · ${range}`} action={<StatusBadge status={dataMode} label={dataMode === 'live' ? 'REAL DATA' : undefined} />} className="span-8">
          <SentimentChart points={sentimentPoints} />
        </Panel>
        <Panel title="Emotion Distribution" subtitle="Latest analyzed window" className="span-4">
          <EmotionBars emotions={emotionData} />
        </Panel>
      </div>

      <div className="dashboard-grid">
        <Panel title="Conversation Activity" subtitle="Loaded event volume by UTC day and hour" className="span-8">
          <ActivityHeatmap events={eventItems} />
        </Panel>
        <Panel title="Recent Activity" subtitle="Most recently collected and analyzed events" className="span-4 activity-panel">
          {enriched.isLoading ? <LoadingState /> : enriched.data?.items.length ? (
            <div className="activity-list">
              {enriched.data.items.slice(0, 6).map(({ event, analysis }) => (
                <article className="activity-item" key={event.event_id}>
                  <div className="activity-item__icon"><Activity size={15} /></div>
                  <div><div className="activity-item__meta"><PlatformBadge platform={event.platform} /><time>{formatDateTime(event.created_at)}</time></div><p>{event.content.text}</p><span>{analysis ? `${sentenceCase(analysis.sentiment.label)} · ${sentenceCase(analysis.emotions.primary_label ?? 'emotion unavailable')}` : 'Analysis pending'}</span></div>
                </article>
              ))}
            </div>
          ) : <EmptyState />}
        </Panel>
      </div>

      <div className="dashboard-grid">
        <Panel title="Rising Topics & Trend Velocity" subtitle={trends.data?.detail ?? `Engine: ${trends.data?.engine}`} className="span-7">
          {topicItems.length ? (
            <div className="topic-table" role="table" aria-label="Current topic rankings">
              <div className="topic-table__head" role="row"><span>Topic</span><span>Volume</span><span>Velocity</span><span>Status</span></div>
              {topicItems.slice(0, 6).map((topic) => (
                <div className="topic-row" role="row" key={topic.topic_id ?? topic.topic}>
                  <div><strong>{topic.topic}</strong><span>{topic.keywords.slice(0, 3).join(' · ')}</span></div>
                  <b>{topic.volume}</b>
                  <span>{topic.velocity == null ? 'Insufficient' : topic.velocity.toFixed(2)}</span>
                  <StatusBadge status={topic.status} />
                </div>
              ))}
            </div>
          ) : <EmptyState title="No persisted topics" detail="The hashtag fallback is used only when explicitly labeled." />}
        </Panel>
        <Panel title="Influence Network" subtitle="Collected replies, mentions, quotes and reposts" className="span-5 network-panel">
          {graph.data ? <NetworkGraph graph={graph.data} /> : <LoadingState />}
          <div className="network-summary-strip"><span><b>{network.data?.summary.nodes ?? 0}</b> nodes</span><span><b>{network.data?.summary.edges ?? 0}</b> edges</span><span><b>{network.data?.summary.communities ?? 0}</b> communities</span></div>
        </Panel>
      </div>

      <Panel title="Data Sources" subtitle="Implementation state and locally stored real data">
        <div className="source-grid">
          <SourceCard name="X / Twitter" status={platformSummary('x') ? 'LIVE DATA' : 'NO STORED DATA'} detail={health.data?.x_api.status === 'PASS' ? 'Collector configured' : 'Collector currently paused'} summary={platformSummary('x')} />
          <SourceCard name="Telegram" status={platformSummary('telegram') ? 'LIVE DATA' : 'NO STORED DATA'} detail={health.data?.telegram_api.status === 'PASS' ? 'Authorized session configured' : 'Collector currently paused'} summary={platformSummary('telegram')} />
          <SourceCard name="YouTube" status="COMING SOON" detail="Comment ingestion is not implemented" />
          <SourceCard name="Reddit" status="COMING SOON" detail="Post and comment ingestion is not implemented" />
          <SourceCard name="Meta platforms" status="PLANNED" detail="Instagram and Facebook adapters are inactive" />
        </div>
      </Panel>
      <span className="sr-only">Scheduler jobs loaded: {jobs.data?.jobs.length ?? 0}. Current positive sentiment: {latestSentiment?.positive_ratio ?? 'unavailable'}.</span>
    </div>
  )
}

function SourceCard({ name, status, detail, summary }: { name: string; status: string; detail: string; summary?: import('../types/system').PlatformDataSummary }) {
  return (
    <article className={`source-card ${summary ? 'source-card--implemented' : 'source-card--planned'}`}>
      <div className="source-card__top"><strong>{name}</strong><StatusBadge status={summary ? 'live' : 'skipped'} label={status} /></div>
      <p>{detail}</p>
      {summary && <span>{formatNumber(summary.real_event_count)} real events</span>}
    </article>
  )
}
