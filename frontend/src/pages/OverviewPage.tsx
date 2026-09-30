import { Activity, ArrowUpRight, GitBranch, MessageSquareText, RadioTower, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { ActivityHeatmap } from '../charts/ActivityHeatmap'
import { EmotionBars } from '../charts/EmotionBars'
import { SentimentChart } from '../charts/SentimentChart'
import { Panel } from '../components/Panel'
import { PlatformBadge } from '../components/PlatformBadge'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { TimeRangeSelector, type TimeRange } from '../components/TimeRangeSelector'
import { useOverviewData, useTopics } from '../hooks/useApiQueries'
import { NetworkGraph } from '../network/NetworkGraph'
import { emotionTotals, filterTemporalRange, sentimentShift } from '../utils/dashboard'
import { formatDateTime, formatNumber, sentenceCase } from '../utils/format'
import { Link } from 'react-router-dom'

export function OverviewPage() {
  const [range, setRange] = useState<TimeRange>('24H')
  const [health, jobs, events, enriched, sentiment, emotions, trends, network, graph] = useOverviewData()
  const topics = useTopics()
  const essential = [health, events, sentiment, trends, network]
  const error = essential.find((query) => query.error)?.error
  if (essential.some((query) => query.isLoading)) return <LoadingState />
  if (error) return <ErrorState error={error} />

  const eventItems = events.data?.items ?? []
  const sentimentPoints = filterTemporalRange(sentiment.data?.rolling_1h ?? [], range)
  const positiveShareChange = sentimentShift(sentimentPoints)
  const emotionData = emotionTotals(filterTemporalRange(emotions.data?.rolling_1h ?? [], range))
  const topicItems = trends.data?.items ?? []
  const latestSentiment = sentimentPoints.at(-1)
  const hasReal = enriched.data?.items.some(({ event }) => !event.source_metadata.replay)
  const hasReplay = enriched.data?.items.some(({ event }) => Boolean(event.source_metadata.replay))
  const dataMode = hasReal && hasReplay ? 'mixed' : hasReal ? 'live' : hasReplay ? 'replay' : 'idle'
  const platformSummary = (platform: string) => health.data?.platforms.find((item) => item.platform === platform)
  const sourceRows = [
    { id: 'x', label: 'X / Twitter', health: health.data?.x_api.status },
    { id: 'telegram', label: 'Telegram', health: health.data?.telegram_api.status },
    { id: 'youtube', label: 'YouTube', health: health.data?.youtube_api.status },
  ]

  return (
    <div className="page-stack overview-page">
      <p className="overview-intro">Public conversation intelligence grounded in stored events and source timestamps.</p>
      <section className="overview-stage" aria-label="Audience intelligence overview">
        <div className="overview-stage__headline">
          <div><span className="overview-kicker">STORED CANONICAL EVENTS</span><strong>{formatNumber(health.data?.event_count ?? 0)}</strong><p>{formatNumber(health.data?.real_event_count ?? 0)} real · {formatNumber(health.data?.replay_event_count ?? 0)} replay</p></div>
          <div className="overview-stage__comparisons" aria-label="Latest analyzed source-time window">
            <div><span>Positive</span><strong>{latestSentiment ? `${(latestSentiment.positive_ratio * 100).toFixed(1)}%` : '—'}</strong></div>
            <div><span>Neutral</span><strong>{latestSentiment ? `${(latestSentiment.neutral_ratio * 100).toFixed(1)}%` : '—'}</strong></div>
            <div><span>Negative</span><strong>{latestSentiment ? `${(latestSentiment.negative_ratio * 100).toFixed(1)}%` : '—'}</strong></div>
            <small>Latest analyzed source-time window · {latestSentiment?.event_count ?? 0} events</small>
          </div>
        </div>
        <div className="overview-signals">
          <Link to="/live-feed" className="overview-signal"><span className="overview-signal__icon"><RadioTower size={18} /></span><span className="overview-signal__name">Collection</span><strong>{formatNumber(health.data?.real_event_count ?? 0)}</strong><small>real stored events</small><ArrowUpRight className="overview-signal__arrow" size={19} /></Link>
          <Link to="/sentiment" className="overview-signal"><span className="overview-signal__icon"><MessageSquareText size={18} /></span><span className="overview-signal__name">Sentiment</span><strong>{positiveShareChange == null ? '—' : `${positiveShareChange >= 0 ? '+' : ''}${(positiveShareChange * 100).toFixed(1)} pp`}</strong><small>{positiveShareChange == null ? 'Insufficient history' : 'positive share vs prior window'}</small><ArrowUpRight className="overview-signal__arrow" size={19} /></Link>
          <Link to="/trends" className="overview-signal"><span className="overview-signal__icon"><TrendingUp size={18} /></span><span className="overview-signal__name">Topics</span><strong>{topics.data ? formatNumber(topics.data.items.length) : '—'}</strong><small>persisted BERTrend topics</small><ArrowUpRight className="overview-signal__arrow" size={19} /></Link>
          <Link to="/network" className="overview-signal"><span className="overview-signal__icon"><GitBranch size={18} /></span><span className="overview-signal__name">Interactions</span><strong>{formatNumber(network.data?.summary.edges ?? 0)}</strong><small>observed graph edges</small><ArrowUpRight className="overview-signal__arrow" size={19} /></Link>
        </div>
        <div className="overview-stage__lower">
          <section className="overview-coverage" aria-label="Platform coverage">
            <header><h2>Source coverage</h2><span>Stored corpus</span></header>
            <div className="overview-coverage__rows">{sourceRows.map((source) => {
              const summary = platformSummary(source.id)
              return <div className="overview-coverage__row" key={source.id}><span className="overview-coverage__mark">{source.id === 'telegram' ? 'TG' : source.id === 'youtube' ? 'YT' : 'X'}</span><div><strong>{source.label}</strong><small>{source.health === 'PASS' ? 'Configured · not necessarily collecting' : 'Collector unavailable or paused'}</small></div><b>{formatNumber(summary?.real_event_count ?? 0)}</b></div>
            })}</div>
            <p>{health.data?.replay_event_count ? `${formatNumber(health.data.replay_event_count)} replay events are reported separately.` : 'No replay events stored.'}</p>
          </section>
          <section className="overview-primary-chart" aria-label="Sentiment over source time">
            <header><div><span className="overview-kicker">CHRONOLOGY</span><h2>Sentiment over time</h2><p>Positive, neutral and negative shares · source-time windows</p></div><TimeRangeSelector value={range} onChange={setRange} /></header>
            <SentimentChart points={sentimentPoints} />
            <footer><span>{sentimentPoints.length} measured windows</span><StatusBadge status={dataMode} label={dataMode === 'live' ? 'STORED REAL DATA' : undefined} /></footer>
          </section>
        </div>
      </section>

      <div className="dashboard-grid">
        <Panel title="Emotion distribution" subtitle="Latest analyzed window · model-estimated scores" className="span-5"><EmotionBars emotions={emotionData} /></Panel>
        <Panel title="Conversation activity" subtitle={`UTC day and hour · ${eventItems.length} recently loaded events, not the full corpus`} className="span-7"><ActivityHeatmap events={eventItems} /></Panel>
      </div>

      <div className="dashboard-grid">
        <Panel title="Recent conversations" subtitle="Most recently collected and analyzed events" className="span-6 activity-panel">
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
        <Panel title="Topic measurements" subtitle={trends.data?.detail ?? `Engine: ${trends.data?.engine}`} className="span-6">
          {topicItems.length ? <div className="topic-table" role="table" aria-label="Latest topic measurements"><div className="topic-table__head" role="row"><span>Topic</span><span>Volume</span><span>Velocity</span><span>Status</span></div>{topicItems.slice(0, 6).map((topic) => <div className="topic-row" role="row" key={topic.topic_id ?? topic.topic}><div><strong>{topic.topic}</strong><span>{topic.keywords.slice(0, 3).join(' · ')}</span></div><b>{topic.volume}</b><span>{topic.velocity == null ? 'Insufficient' : topic.velocity.toFixed(2)}</span><StatusBadge status={topic.velocity == null ? 'INSUFFICIENT_DATA' : topic.status} label={topic.velocity == null ? 'First observation' : undefined} /></div>)}</div> : <EmptyState title="No persisted topics" detail="The hashtag fallback is used only when explicitly labeled." />}
        </Panel>
      </div>

      <div className="dashboard-grid">
        <Panel title="Interaction preview" subtitle="Observed relationships, not follower connections" className="span-12 network-panel">
          {graph.data ? <NetworkGraph graph={graph.data} /> : <LoadingState />}
          <div className="network-summary-strip"><span><b>{network.data?.summary.nodes ?? 0}</b> nodes</span><span><b>{network.data?.summary.edges ?? 0}</b> edges</span><span><b>{network.data?.summary.communities ?? 0}</b> communities</span></div>
          <Link className="panel-link" to="/network">Explore interaction map →</Link>
        </Panel>
      </div>

      <Panel title="Data Sources" subtitle="Implementation state and locally stored real data">
        <div className="source-grid">
          <SourceCard name="X / Twitter" status={platformSummary('x') ? 'STORED DATA' : 'NO STORED DATA'} detail={health.data?.x_api.status === 'PASS' ? 'Collector configured' : 'Collector currently paused'} summary={platformSummary('x')} />
          <SourceCard name="Telegram" status={platformSummary('telegram') ? 'STORED DATA' : 'NO STORED DATA'} detail={health.data?.telegram_api.status === 'PASS' ? 'Authorized session configured' : 'Collector currently paused'} summary={platformSummary('telegram')} />
          <SourceCard name="YouTube" status={platformSummary('youtube') ? 'AVAILABLE' : health.data?.youtube_api.status === 'PASS' ? 'CONFIGURED' : 'NOT CONFIGURED'} detail="Polling-based comment ingestion (not a live stream)" summary={platformSummary('youtube')} />
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
      <div className="source-card__top"><strong>{name}</strong><StatusBadge status={summary ? 'AVAILABLE' : 'skipped'} label={status} /></div>
      <p>{detail}</p>
      {summary && <span>{formatNumber(summary.real_event_count)} real events</span>}
    </article>
  )
}
