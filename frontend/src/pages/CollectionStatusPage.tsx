import { Play } from 'lucide-react'
import { useState } from 'react'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Stat, Stats } from '../components/Stat'
import { Status } from '../components/Status'
import { ErrorState, LoadingState, Notice } from '../components/States'
import { useRunJob, useSystem } from '../hooks/useApiQueries'
import { formatDuration, formatNumber, formatShortTime, sentenceCase, timeAgo } from '../utils/format'

const JOB_LABELS: Record<string, string> = {
  x_recent_search: 'X collection',
  telegram_collection: 'Telegram collection',
  youtube_collection: 'YouTube collection',
  nlp_processing: 'Sentiment, emotion and irony',
  graph_refresh: 'Interaction graph',
  trend_analysis: 'Topic discovery',
  demographics_refresh: 'Demographic estimates',
  audience_profile_sync: 'Audience Lab profiles',
}
const ORDER = Object.keys(JOB_LABELS)

export function CollectionStatusPage() {
  const [health, jobs] = useSystem()
  const run = useRunJob()
  const [lastError, setLastError] = useState<string | null>(null)
  if (health.isLoading || jobs.isLoading) return <div className="page"><LoadingState label="Loading jobs" /></div>
  if (health.error || jobs.error) return <div className="page"><ErrorState error={health.error ?? jobs.error} /></div>
  const all = [...(jobs.data?.jobs ?? [])].sort((a, b) => (ORDER.indexOf(a.name) + 99 * Number(!ORDER.includes(a.name))) - (ORDER.indexOf(b.name) + 99 * Number(!ORDER.includes(b.name))))
  const failing = all.filter((job) => job.status === 'FAIL')
  const runs = all.reduce((sum, job) => sum + job.run_count, 0)
  const processed = all.reduce((sum, job) => sum + job.total_processed_count, 0)
  const start = (name: string) => {
    setLastError(null)
    run.mutate(name, { onError: (error) => setLastError(error instanceof Error ? error.message : 'Run failed') })
  }

  return (
    <div className="page">
      <PageHeader
        title="Jobs"
        description={jobs.data?.running ? `Scheduler running since ${formatShortTime(jobs.data.started_at)}` : 'Scheduler is off. Set SCHEDULER_ENABLED=true in .env to collect continuously; jobs can still be run here.'}
        actions={<Status status={jobs.data?.running ? 'running' : 'paused'} label={jobs.data?.running ? 'Scheduler running' : 'Scheduler off'} />}
      />
      <Stats label="Job totals">
        <Stat label="Stored events" value={health.data?.event_count ?? 0} />
        <Stat label="Runs since start" value={runs} />
        <Stat label="Items processed" value={processed} />
        <Stat label="Failing" value={failing.length} tone={failing.length ? 'neg' : 'default'} />
      </Stats>
      {lastError && <Notice tone="error">{lastError}</Notice>}
      <Panel flush title="Scheduled jobs" description="Run any job now. Collection jobs read the sources configured on the Sources page.">
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Job</th><th>Status</th><th>Every</th><th>Last run</th><th>Next run</th><th className="r">Last / total</th><th className="r">Took</th><th /></tr></thead>
            <tbody>
              {all.map((job) => {
                const busy = job.status === 'RUNNING' || (run.isPending && run.variables === job.name)
                return (
                  <tr key={job.name}>
                    <td style={{ minWidth: 260 }}>
                      <strong>{JOB_LABELS[job.name] ?? sentenceCase(job.name)}</strong>
                      <div className="faint" style={{ fontSize: 12, maxWidth: 420 }}>{job.error ?? job.detail ?? 'Not run yet'}</div>
                    </td>
                    <td><Status status={busy ? 'running' : job.status} label={busy ? 'Running' : undefined} /></td>
                    <td className="num">{formatDuration(job.interval_seconds)}</td>
                    <td className="num" title={job.last_finished_at ?? undefined}>{job.last_finished_at ? timeAgo(job.last_finished_at) : '–'}</td>
                    <td className="num">{jobs.data?.running && job.next_run_at ? formatShortTime(job.next_run_at) : '–'}</td>
                    <td className="r">{formatNumber(job.processed_count)} / {formatNumber(job.total_processed_count)}</td>
                    <td className="r">{job.duration_ms == null ? '–' : job.duration_ms < 1000 ? `${Math.round(job.duration_ms)} ms` : formatDuration(job.duration_ms / 1000)}</td>
                    <td className="r"><button type="button" className="btn btn--sm" disabled={busy} onClick={() => start(job.name)} aria-label={`Run ${JOB_LABELS[job.name] ?? job.name} now`}>{busy ? <span className="spinner" /> : <Play size={12} />} Run</button></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
