import { ArrowDown, ArrowUp } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Stat, Stats } from '../components/Stat'
import { Status } from '../components/Status'
import { EmptyState, ErrorState, LoadingState, Notice } from '../components/States'
import { useTopics, useTrends } from '../hooks/useApiQueries'
import type { TopicSummary } from '../types/analytics'
import { topicState } from '../utils/dashboard'
import { formatNumber, formatShortTime } from '../utils/format'

type SortKey = 'volume' | 'growth' | 'velocity' | 'window_end'

export function TrendsPage() {
  const trends = useTrends()
  const topics = useTopics()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'volume', desc: true })

  const all = useMemo(() => topics.data?.items ?? [], [topics.data])
  const items = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const filtered = all.filter((topic) => !needle || `${topic.topic} ${topic.keywords.join(' ')}`.toLowerCase().includes(needle))
    const value = (topic: TopicSummary) => sort.key === 'window_end' ? new Date(topic.window_end ?? 0).getTime() : topic[sort.key] ?? -Infinity
    return [...filtered].sort((a, b) => (sort.desc ? value(b) - value(a) : value(a) - value(b)))
  }, [all, search, sort])

  if (trends.isLoading || topics.isLoading) return <div className="page"><LoadingState label="Loading topics" /></div>
  if (trends.error || topics.error) return <div className="page"><ErrorState error={trends.error ?? topics.error} /></div>

  const measured = all.filter((topic) => topic.velocity != null)
  const count = (statuses: string[]) => measured.filter((topic) => statuses.includes(topic.status)).length
  const header = (key: SortKey, label: string) => (
    <button type="button" className="th-sort" aria-sort={sort.key === key ? (sort.desc ? 'descending' : 'ascending') : undefined} onClick={() => setSort((current) => ({ key, desc: current.key === key ? !current.desc : true }))}>
      {label}{sort.key === key && (sort.desc ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}
    </button>
  )

  return (
    <div className="page">
      <PageHeader title="Topics" description={`Discovered by ${trends.data?.engine ?? 'the trend engine'} from collected text, measured per source-time window`} />
      <Stats label="Topic summary">
        <Stat label="Topics" value={all.length} meta={`${measured.length} measured more than once`} />
        <Stat label="Rising" tone="pos" value={count(['rising', 'explosive'])} meta="velocity above zero" />
        <Stat label="Sustained" value={count(['sustained'])} />
        <Stat label="Cooling" value={count(['cooling'])} />
        <Stat label="First seen" tone="accent" value={all.length - measured.length} meta="direction not known yet" />
      </Stats>
      {trends.data?.fallback && <Notice>Topic modelling is unavailable, so these are hashtag frequencies, not discovered topics.</Notice>}
      <Panel
        flush
        title={<input className="input" style={{ width: 280 }} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filter topics or keywords" aria-label="Filter topics" />}
        actions={<span className="faint" style={{ fontSize: 12.5 }}>{items.length} of {all.length}</span>}
      >
        {items.length ? (
          <div className="table-wrap">
            <table className="table">
              <thead><tr>
                <th>Topic</th>
                <th className="r">{header('volume', 'Volume')}</th>
                <th className="r">{header('growth', 'Growth')}</th>
                <th className="r">{header('velocity', 'Velocity')}</th>
                <th>{header('window_end', 'Latest window')}</th>
                <th>Status</th>
              </tr></thead>
              <tbody>
                {items.map((topic) => {
                  const state = topicState(topic)
                  const open = () => topic.topic_id && navigate(`/trends/${topic.topic_id}`)
                  return (
                    <tr key={topic.topic_id ?? topic.topic} className={topic.topic_id ? 'is-clickable' : ''} tabIndex={topic.topic_id ? 0 : undefined} onClick={open} onKeyDown={(event) => { if (event.key === 'Enter') open() }}>
                      <td><strong>{topic.topic}</strong><div className="faint" style={{ fontSize: 12 }}>{topic.keywords.slice(0, 5).join(', ') || 'No keywords'}</div></td>
                      <td className="r"><b>{formatNumber(topic.volume)}</b></td>
                      <td className="r">{topic.growth == null ? '–' : `${topic.growth >= 0 ? '+' : ''}${(topic.growth * 100).toFixed(0)}%`}</td>
                      <td className="r">{topic.velocity == null ? '–' : topic.velocity.toFixed(2)}</td>
                      <td className="num" style={{ whiteSpace: 'nowrap' }}>{formatShortTime(topic.window_end)}</td>
                      <td><Status status={state.status} label={state.label} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : <div className="panel__body"><EmptyState title={all.length ? 'No topics match this filter' : 'No topics yet'} detail={all.length ? undefined : trends.data?.detail ?? 'The trend job needs more collected text.'} /></div>}
      </Panel>
      <p className="faint" style={{ fontSize: 12.5 }}>Velocity is documents per hour between matched windows. A topic seen in only one window has no direction yet.</p>
    </div>
  )
}
