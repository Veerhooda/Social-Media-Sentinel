import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { addSource, deleteSource, updateSource } from '../api/sources'
import type { CollectionSource, PlatformCollector, SourcePlatform } from '../api/sources'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { PlatformIcon } from '../components/Platform'
import { platformLabel } from '../utils/platform'
import { Stat, Stats } from '../components/Stat'
import { Status } from '../components/Status'
import { ErrorState, LoadingState, Notice } from '../components/States'
import { queryKeys, useRunJob, useSources, useSystem } from '../hooks/useApiQueries'
import type { JobStatus, PlatformDataSummary } from '../types/system'
import { formatDuration, formatNumber, timeAgo } from '../utils/format'

const PLACEHOLDER: Record<SourcePlatform, string> = {
  telegram: 'Public channel: @name or t.me/name',
  youtube: 'Video URL or 11-character id',
  x: 'Search query, e.g. "climate policy" lang:en',
}
const WHAT: Record<SourcePlatform, string> = {
  telegram: 'Public channel posts, newest first. Each run fetches messages after the last one stored.',
  youtube: 'Comments and replies on a video. Each run re-reads the newest pages; duplicates are skipped.',
  x: 'Recent search results for a query. Each run continues from the newest post already stored.',
}

export function DataSourcesPage() {
  const sources = useSources()
  const [health, jobs] = useSystem()
  if (sources.isLoading || health.isLoading) return <div className="page"><LoadingState label="Loading sources" /></div>
  if (sources.error || health.error) return <div className="page"><ErrorState error={sources.error ?? health.error} /></div>
  const data = sources.data!
  const enabled = data.platforms.reduce((sum, platform) => sum + platform.sources.filter((source) => source.enabled).length, 0)
  const stored = (platform: string) => health.data?.platforms.find((item) => item.platform === platform)
  return (
    <div className="page">
      <PageHeader
        title="Sources"
        description="Channels, videos and queries the collectors read from. Changes apply on the next run."
        actions={<Status status={data.scheduler_running ? 'running' : 'paused'} label={data.scheduler_running ? 'Collecting on schedule' : 'Scheduler off · runs are manual'} />}
      />
      <Stats label="Collection summary">
        <Stat label="Active sources" value={enabled} />
        {data.platforms.map((platform) => <Stat key={platform.platform} label={`${platformLabel(platform.platform)} events`} value={stored(platform.platform)?.real_event_count ?? 0} meta={stored(platform.platform)?.latest_collected_at ? `last collected ${timeAgo(stored(platform.platform)!.latest_collected_at)}` : 'nothing collected yet'} />)}
      </Stats>
      {data.platforms.map((collector) => (
        <CollectorPanel key={collector.platform} collector={collector} job={jobs.data?.jobs.find((job) => job.name === collector.job_name)} stored={stored(collector.platform)} schedulerRunning={data.scheduler_running} />
      ))}
    </div>
  )
}

function CollectorPanel({ collector, job, stored, schedulerRunning }: { collector: PlatformCollector; job?: JobStatus; stored?: PlatformDataSummary; schedulerRunning: boolean }) {
  const client = useQueryClient()
  const refresh = () => client.invalidateQueries({ queryKey: queryKeys.sources })
  const [target, setTarget] = useState('')
  const [error, setError] = useState<string | null>(null)
  const run = useRunJob()
  const add = useMutation({
    mutationFn: () => addSource(collector.platform, target),
    onSuccess: () => { setTarget(''); setError(null); void refresh() },
    onError: (failure) => setError(failure instanceof Error ? failure.message : 'Could not add source'),
  })
  const submit = (event: FormEvent) => { event.preventDefault(); if (target.trim()) add.mutate() }
  const busy = job?.status === 'RUNNING' || run.isPending
  const enabled = collector.sources.filter((source) => source.enabled).length

  return (
    <Panel
      flush
      title={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><PlatformIcon platform={collector.platform} size={15} />{platformLabel(collector.platform)}</span>}
      description={WHAT[collector.platform]}
      actions={
        <>
          <Status
            status={!collector.credentials_configured ? 'fail' : job?.status === 'FAIL' ? 'fail' : !enabled ? 'idle' : schedulerRunning ? 'running' : 'paused'}
            label={!collector.credentials_configured ? collector.credential_detail : !enabled ? 'No active sources' : schedulerRunning ? `Every ${formatDuration(collector.interval_seconds)}` : 'Manual only'}
          />
          <button type="button" className="btn btn--sm" disabled={!collector.credentials_configured || !enabled || busy} onClick={() => run.mutate(collector.job_name)}>
            {busy ? <span className="spinner" /> : <Play size={12} />} Collect now
          </button>
        </>
      }
      footer={
        <>
          <span>{job?.last_finished_at ? `Last run ${timeAgo(job.last_finished_at)}: ${job.error ?? job.detail ?? ''}` : 'Not run since the server started'}</span>
          <span className="num">{formatNumber(stored?.real_event_count ?? 0)} stored</span>
        </>
      }
    >
      {collector.sources.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th style={{ width: 52 }}>On</th><th>Source</th><th>Last run</th><th className="r">Last run stored</th><th className="r">Total stored</th><th /></tr></thead>
            <tbody>{collector.sources.map((source) => <SourceRow key={source.source_id} source={source} onChange={refresh} />)}</tbody>
          </table>
        </div>
      )}
      <form onSubmit={submit} style={{ display: 'flex', gap: 8, padding: '12px 16px', borderTop: collector.sources.length ? '1px solid var(--line)' : undefined }}>
        <input className="input" value={target} onChange={(event) => setTarget(event.target.value)} placeholder={PLACEHOLDER[collector.platform]} aria-label={`Add ${platformLabel(collector.platform)} source`} style={{ maxWidth: 420 }} />
        <button type="submit" className="btn" disabled={!target.trim() || add.isPending}><Plus size={14} /> Add</button>
      </form>
      {error && <div style={{ padding: '0 16px 12px' }}><Notice tone="error">{error}</Notice></div>}
    </Panel>
  )
}

function SourceRow({ source, onChange }: { source: CollectionSource; onChange: () => void }) {
  const toggle = useMutation({ mutationFn: () => updateSource(source.source_id, { enabled: !source.enabled }), onSettled: onChange })
  const remove = useMutation({ mutationFn: () => deleteSource(source.source_id), onSettled: onChange })
  const [confirming, setConfirming] = useState(false)
  useEffect(() => {
    if (!confirming) return
    const timer = window.setTimeout(() => setConfirming(false), 4000)
    return () => window.clearTimeout(timer)
  }, [confirming])
  const href = source.platform === 'telegram' ? `https://t.me/${source.target}` : source.platform === 'youtube' ? `https://www.youtube.com/watch?v=${source.target}` : null
  return (
    <tr style={{ opacity: source.enabled ? 1 : 0.55, transition: 'opacity var(--t)' }}>
      <td><button type="button" role="switch" className="switch" aria-checked={source.enabled} aria-label={`${source.enabled ? 'Disable' : 'Enable'} ${source.target}`} disabled={toggle.isPending} onClick={() => toggle.mutate()} /></td>
      <td>
        {href ? <a href={href} target="_blank" rel="noopener noreferrer"><strong>{source.target}</strong></a> : <strong>{source.target}</strong>}
        {source.label && <div className="faint" style={{ fontSize: 12 }}>{source.label}</div>}
      </td>
      <td style={{ maxWidth: 380 }}>
        {source.last_run_at ? <><Status status={source.last_status ?? 'neutral'} label={timeAgo(source.last_run_at)} /><div className="faint" style={{ fontSize: 12 }}>{source.last_detail}</div></> : <span className="faint">Waiting for first run</span>}
      </td>
      <td className="r">{formatNumber(source.last_stored)}</td>
      <td className="r"><b>{formatNumber(source.total_stored)}</b></td>
      <td className="r">
        {confirming
          ? <button type="button" className="btn btn--sm btn--danger" disabled={remove.isPending} onClick={() => remove.mutate()}>Remove · keeps stored events</button>
          : <button type="button" className="btn btn--ghost btn--icon btn--danger" onClick={() => setConfirming(true)} aria-label={`Remove ${source.target}`}><Trash2 size={14} /></button>}
      </td>
    </tr>
  )
}
