import { Activity, Clock, Database, Layers3 } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useSystem } from '../hooks/useApiQueries'
import { formatDateTime, formatNumber } from '../utils/format'

export function CollectionStatusPage() {
  const [health, jobs] = useSystem()
  if (health.isLoading || jobs.isLoading) return <LoadingState />
  if (health.error || jobs.error) return <ErrorState error={health.error ?? jobs.error} />
  const allJobs = jobs.data?.jobs ?? []
  const processed = allJobs.reduce((sum, job) => sum + job.total_processed_count, 0)
  const failures = allJobs.filter((job) => job.status === 'FAIL').length
  return (
    <div className="page-stack"><PageHeader title="Collection Status" subtitle="Operational scheduler and analytical job observability." actions={<StatusBadge status={jobs.data?.running ? 'running' : 'skipped'} label={jobs.data?.running ? 'Scheduler running' : 'Scheduler stopped'} />} />
      <div className="metric-grid metric-grid--four"><MetricCard label="Stored Events" value={formatNumber(health.data?.event_count ?? 0)} detail="PostgreSQL canonical rows" icon={Database} /><MetricCard label="Job Runs" value={formatNumber(allJobs.reduce((sum, job) => sum + job.run_count, 0))} detail="this process lifetime" icon={Activity} tone="blue" /><MetricCard label="Processed" value={formatNumber(processed)} detail="cumulative job count" icon={Layers3} tone="green" /><MetricCard label="Failures" value={failures} detail="currently failed jobs" icon={Clock} tone={failures ? 'pink' : 'purple'} /></div>
      <Panel title="Scheduled Jobs" subtitle="No controls are exposed; backend configuration owns scheduling"><div className="jobs-table"><div className="jobs-table__header"><span>Job</span><span>Status</span><span>Last run</span><span>Next run</span><span>Last / Total</span><span>Duration</span><span>Overlap skips</span></div>{allJobs.map((job) => <div className="jobs-table__row" key={job.name}><div><strong>{job.name.replaceAll('_', ' ')}</strong><span>{job.detail ?? job.error ?? 'No execution yet'}</span></div><StatusBadge status={job.status} /><time>{formatDateTime(job.last_finished_at)}</time><time>{formatDateTime(job.next_run_at)}</time><b>{job.processed_count} / {job.total_processed_count}</b><span>{job.duration_ms == null ? '—' : `${job.duration_ms.toFixed(1)} ms`}</span><span>{job.overlap_skips}</span></div>)}</div></Panel>
    </div>
  )
}

