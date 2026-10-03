import { ArrowRight } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ActivityHeatmap } from '../charts/ActivityHeatmap'
import { SentimentLegend, VolumeChart } from '../charts/VolumeChart'
import { Bars } from '../components/Bars'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Platform } from '../components/Platform'
import { platformLabel } from '../utils/platform'
import { Segmented } from '../components/Segmented'
import { Delta, Stat, Stats } from '../components/Stat'
import { Status } from '../components/Status'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { useOverviewData, useSources, useTopics } from '../hooks/useApiQueries'
import type { EnrichedEvent } from '../types/events'
import { emotionTotals, SERIES_RANGES, selectSeries, splitNeutralEmotion, topicState, type SeriesRange } from '../utils/dashboard'
import { formatDuration, formatNumber, pct, sentenceCase, timeAgo } from '../utils/format'
import { nodeLabel } from '../utils/network'

export function OverviewPage() {
  const [range, setRange] = useState<SeriesRange>('24h')
  const [mode, setMode] = useState<'count' | 'share'>('count')
  const [health, , events, enriched, sentiment, emotions, trends, network] = useOverviewData()
  const topics = useTopics()
  const sources = useSources()

  const points = useMemo(() => selectSeries(sentiment.data, range), [sentiment.data, range])
  const emotionPoints = useMemo(() => selectSeries(emotions.data, range), [emotions.data, range])

  const essential = [health, sentiment, trends, network]
  const error = essential.find((query) => query.error)?.error
  if (essential.some((query) => query.isLoading)) return <div className="page"><LoadingState label="Loading overview" /></div>
  if (error) return <div className="page"><ErrorState error={error} /></div>

  const latest = points.at(-1)
  const previous = points.at(-2)
  const delta = (key: 'positive_ratio' | 'negative_ratio' | 'irony_rate') =>
    latest && previous ? (latest[key] - previous[key]) * 100 : null
  const platforms = (health.data?.platforms ?? []).filter((platform) => platform.real_event_count > 0)
  const newest = platforms.map((platform) => platform.latest_collected_at).filter(Boolean).sort().at(-1)
  const topicItems = topics.data?.items ?? trends.data?.items ?? []
  const rising = topicItems.filter((topic) => topic.velocity != null && ['rising', 'explosive'].includes(topic.status)).length
  const { neutral, emotions: emotionScores } = splitNeutralEmotion(emotionTotals(emotionPoints))
  const emotionItems = Object.entries(emotionScores).map(([label, value]) => ({ label: sentenceCase(label), value, display: pct(value) }))
  const topAccounts = [...(network.data?.summary.metrics ?? [])].sort((a, b) => b.pagerank - a.pagerank).slice(0, 5)
  const rangeLabel = SERIES_RANGES.find((item) => item.value === range)?.label

  return (
    <div className="page">
      <PageHeader
        title="Overview"
        description={`${formatNumber(health.data?.real_event_count ?? 0)} collected events from ${platforms.length} platform${platforms.length === 1 ? '' : 's'}${newest ? ` · newest collected ${timeAgo(newest)}` : ''}`}
        actions={<Segmented label="Time range" value={range} options={SERIES_RANGES} onChange={setRange} />}
      />

      <Stats label="Key measures">
        <Stat label="Events stored" value={health.data?.real_event_count ?? 0} to="/live-feed" meta={health.data?.replay_event_count ? `${formatNumber(health.data.replay_event_count)} replay kept separate` : `across ${platforms.length} platforms`} />
        <Stat label="Positive" value={latest ? latest.positive_ratio * 100 : null} format={(n) => n.toFixed(1)} unit="%" tone="pos" to="/sentiment" meta={<><Delta value={delta('positive_ratio')} />{latest && <span>latest window · {latest.event_count} events</span>}</>} />
        <Stat label="Negative" value={latest ? latest.negative_ratio * 100 : null} format={(n) => n.toFixed(1)} unit="%" tone="neg" to="/sentiment" meta={<><Delta value={delta('negative_ratio')} invert />{latest && <span>latest window</span>}</>} />
        <Stat label="Irony" value={latest ? latest.irony_rate * 100 : null} format={(n) => n.toFixed(1)} unit="%" tone="sar" to="/sentiment" meta={<><Delta value={delta('irony_rate')} invert />{latest && <span>of analysed posts</span>}</>} />
        <Stat label="Topics" value={topicItems.length} to="/trends" meta={rising ? `${rising} rising` : 'none rising'} />
        <Stat label="Interactions" value={network.data?.summary.edges ?? 0} to="/network" meta={`${formatNumber(network.data?.summary.nodes ?? 0)} accounts`} />
      </Stats>

      <div className="grid">
        <Panel
          className="col-8"
          title="Conversation volume"
          description={latest ? `${rangeLabel === 'All' ? 'All data' : `Last ${rangeLabel} of data`}, ending ${new Date(latest.window_end).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} · ${range === '24h' ? 'hourly windows' : 'daily windows'}` : 'Analysed events by sentiment'}
          actions={<Segmented label="Chart values" value={mode} options={[{ value: 'count', label: 'Events' }, { value: 'share', label: 'Share' }]} onChange={setMode} />}
          footer={<><SentimentLegend /><span>{points.length} windows</span></>}
        >
          <VolumeChart points={points} mode={mode} />
        </Panel>

        <Panel className="col-4" title="Sources" flush footer={<Link to="/data-sources">Manage sources <ArrowRight size={13} style={{ display: 'inline', verticalAlign: '-2px' }} /></Link>}>
          <div className="rows">
            {(sources.data?.platforms ?? []).map((collector) => {
              const stored = health.data?.platforms.find((platform) => platform.platform === collector.platform)
              const enabled = collector.sources.filter((source) => source.enabled).length
              const state = !collector.credentials_configured ? ['idle', 'No credentials'] : !enabled ? ['idle', 'No sources'] : sources.data?.scheduler_running ? ['ok', `Every ${formatDuration(collector.interval_seconds)}`] : ['idle', 'Paused']
              return (
                <Link className="row" key={collector.platform} to="/data-sources">
                  <div>
                    <div className="row__title"><Platform platform={collector.platform} /></div>
                    <div className="row__meta">
                      <Status status={state[0]} label={state[1]} />
                      <span>{stored?.latest_collected_at ? `last ${timeAgo(stored.latest_collected_at)}` : 'nothing collected'}</span>
                    </div>
                  </div>
                  <div className="row__value">{formatNumber(stored?.real_event_count ?? 0)}</div>
                </Link>
              )
            })}
            {!sources.data && <div className="row"><LoadingState /></div>}
          </div>
        </Panel>

        <Panel className="col-7" title="Latest conversations" description="Newest by source time" flush footer={<Link to="/live-feed">Open conversations</Link>}>
          {enriched.data?.items.length ? <div className="rows">{enriched.data.items.slice(0, 6).map((item) => <ConversationRow key={item.event.event_id} item={item} />)}</div> : enriched.isLoading ? <div className="panel__body"><LoadingState /></div> : <div className="panel__body"><EmptyState /></div>}
        </Panel>

        <Panel className="col-5" title="Topics" description={trends.data?.engine ? `${trends.data.engine} · by latest volume` : undefined} flush footer={<Link to="/trends">All topics</Link>}>
          {topicItems.length ? (
            <div className="rows">
              {[...topicItems].sort((a, b) => b.volume - a.volume).slice(0, 6).map((topic) => {
                const state = topicState(topic)
                const body = <>
                  <div>
                    <div className="row__title truncate">{topic.topic}</div>
                    <div className="row__meta"><Status status={state.status} label={state.label} />{topic.keywords.slice(0, 3).join(', ')}</div>
                  </div>
                  <div className="row__value">{formatNumber(topic.volume)}</div>
                </>
                return topic.topic_id ? <Link className="row" key={topic.topic_id} to={`/trends/${topic.topic_id}`}>{body}</Link> : <div className="row" key={topic.topic}>{body}</div>
              })}
            </div>
          ) : <div className="panel__body"><EmptyState title="No topics yet" detail="Topics appear after the trend job has analysed enough events." /></div>}
        </Panel>

        <Panel className="col-4" title="Emotions" description={`Average model score, latest window${neutral != null ? ` · neutral ${pct(neutral, 0)}` : ''}`}>
          {emotionItems.length ? <Bars label="Emotion scores" items={emotionItems} /> : <EmptyState title="No emotion scores" />}
        </Panel>

        <Panel className="col-4" title="Posting activity" description={`${formatNumber(events.data?.items.length ?? 0)} most recent events, by UTC weekday and hour`}>
          {events.data?.items.length ? <ActivityHeatmap events={events.data.items} /> : <EmptyState />}
        </Panel>

        <Panel className="col-4" title="Most central accounts" description="PageRank in the stored interaction graph" flush footer={<Link to="/network">Open interaction map</Link>}>
          {topAccounts.length ? (
            <div className="rows">
              {topAccounts.map((node) => (
                <Link to="/network" className="row" key={node.node_id}>
                  <div>
                    <div className="row__title truncate">{nodeLabel(node)}</div>
                    <div className="row__meta"><span>{platformLabel(node.node_id.split(':')[0])}</span>{node.community != null && <span>community {node.community}</span>}</div>
                  </div>
                  <div className="row__value">{node.pagerank.toFixed(3)}</div>
                </Link>
              ))}
            </div>
          ) : <div className="panel__body"><EmptyState title="No interactions yet" /></div>}
        </Panel>
      </div>
    </div>
  )
}

function ConversationRow({ item }: { item: EnrichedEvent }) {
  const { event, analysis } = item
  const author = event.author.username ? `@${event.author.username}` : event.author.display_name ?? 'Unknown author'
  return (
    <Link to={`/live-feed?event=${event.event_id}`} className="row" style={{ gridTemplateColumns: 'minmax(0, 1fr)' }}>
      <div>
        <div className="row__meta" style={{ marginTop: 0, marginBottom: 3 }}>
          <Platform platform={event.platform} />
          <span className="truncate" style={{ maxWidth: 200 }}>{author}</span>
          <span>{timeAgo(event.created_at)}</span>
          {analysis && <span className="sentiment"><i className={`dot dot--${analysis.sentiment.label}`} />{analysis.sentiment.label}</span>}
          {analysis?.irony.is_ironic && <span className="sentiment"><i className="dot dot--sarcastic" />ironic</span>}
        </div>
        <p className="clamp-2" style={{ color: 'var(--text)', fontSize: 13.5 }}>{event.content.text || '(no text)'}</p>
      </div>
    </Link>
  )
}
