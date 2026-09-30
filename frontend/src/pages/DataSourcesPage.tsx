import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useSystem } from '../hooks/useApiQueries'
import type { ComponentHealth, PlatformDataSummary } from '../types/system'
import { formatNumber, timeAgo } from '../utils/format'

const plannedSources = [
  { mark: 'R', name: 'Reddit', status: 'COMING SOON', detail: 'Post and comment ingestion is not implemented.' },
  { mark: 'M', name: 'Meta platforms', status: 'PLANNED', detail: 'Instagram and Facebook adapters are inactive.' },
]

export function DataSourcesPage() {
  const [health, jobs] = useSystem()
  if (health.isLoading || jobs.isLoading) return <LoadingState label="Loading source status…" />
  if (health.error || jobs.error) return <ErrorState error={health.error ?? jobs.error} />
  const summary = (platform: string) => health.data?.platforms.find((item) => item.platform === platform)
  const xJob = jobs.data?.jobs.find((job) => job.name === 'x_recent_search')

  return (
    <div className="page-stack">
      <PageHeader title="Data sources" subtitle="Configured collectors, historical stored data, and integrations that are not yet active." />
      <Panel title="Implemented" subtitle="Counts and timestamps come from canonical PostgreSQL events">
        <div className="source-list">
          <ImplementedSource
            mark="X"
            name="X / Twitter"
            mode="Recent Search + Filtered Stream"
            health={health.data!.x_api}
            description={health.data!.x_api.status === 'PASS' ? 'Client configured; collection runs only when explicitly enabled.' : 'Collector not currently configured or running; historical data remains available.'}
            summary={summary('x')}
            lastRun={xJob?.last_finished_at}
          />
          <ImplementedSource
            mark="TG"
            name="Telegram"
            mode="Public history + NewMessage"
            health={health.data!.telegram_api}
            description={health.data!.telegram_api.status === 'PASS' ? 'Authorized session available; collector currently idle.' : 'Collector not currently configured or running; historical data remains available.'}
            summary={summary('telegram')}
          />
          <ImplementedSource
            mark="YT"
            name="YouTube"
            mode="Comment polling (not a live stream)"
            health={health.data!.youtube_api}
            description={health.data!.youtube_api.status === 'PASS' ? 'API key configured; collection is manually triggered.' : 'Adapter implemented; API key not configured.'}
            summary={summary('youtube')}
          />
        </div>
      </Panel>
      <Panel title="Planned sources" subtitle="No operational metrics are shown for unimplemented adapters">
        <div className="source-list source-list--planned">
          {plannedSources.map((source) => (
            <article className="source-row source-row--planned" key={source.name}>
              <div className="source-logo source-logo--muted">{source.mark}</div>
              <div><h3>{source.name}</h3><p>{source.detail}</p></div>
              <span className="source-row__availability">No collector or stored source metrics</span>
              <StatusBadge status="skipped" label={source.status} />
            </article>
          ))}
        </div>
      </Panel>
    </div>
  )
}

function ImplementedSource({
  mark,
  name,
  mode,
  health,
  description,
  summary,
  lastRun,
}: {
  mark: string
  name: string
  mode: string
  health: ComponentHealth
  description: string
  summary?: PlatformDataSummary
  lastRun?: string | null
}) {
  const hasRealData = Boolean(summary?.real_event_count)
  return (
    <article className="source-row source-row--primary">
      <div className="source-logo">{mark}</div>
      <div>
        <h3>{name}</h3>
        <p>{description}</p>
      </div>
      <dl>
        <div><dt>Mode</dt><dd>{mode}</dd></div>
        <div><dt>Latest collected</dt><dd>{timeAgo(summary?.latest_collected_at ?? lastRun)}</dd></div>
        <div><dt>Real events</dt><dd>{summary ? formatNumber(summary.real_event_count) : 'No data'}</dd></div>
      </dl>
      <StatusBadge status={hasRealData ? 'AVAILABLE' : health.status} label={hasRealData ? 'STORED DATA' : health.status === 'PASS' ? 'CONFIGURED' : health.status} />
    </article>
  )
}
