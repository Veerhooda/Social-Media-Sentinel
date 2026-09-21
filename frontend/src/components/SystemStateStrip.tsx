import type { HealthResponse, SchedulerStatus } from '../types/system'
import { formatNumber, timeAgo } from '../utils/format'

export function SystemStateStrip({ health, jobs }: { health: HealthResponse; jobs?: SchedulerStatus }) {
  const source = (platform: string) => health.platforms.find((item) => item.platform === platform)
  const x = source('x')
  const telegram = source('telegram')
  const mode = health.real_event_count && health.replay_event_count
    ? 'Mixed real and replay data'
    : health.real_event_count
      ? 'Real collected data'
      : health.replay_event_count
        ? 'Replay data'
        : 'No collected data'

  return (
    <section className="system-state" aria-label="Current data and system state">
      <div className="system-state__lead">
        <span className="eyebrow">CURRENT STATE</span>
        <strong>{mode}</strong>
        <span>{formatNumber(health.event_count)} canonical events in PostgreSQL</span>
      </div>
      <SourceStat label="X" count={x?.real_event_count ?? 0} detail={health.x_api.detail} />
      <SourceStat label="Telegram" count={telegram?.real_event_count ?? 0} detail={health.telegram_api.detail} />
      <div className="system-state__item">
        <span className={`source-dot ${jobs?.running ? 'is-active' : ''}`} />
        <div><strong>Scheduler</strong><span>{jobs?.running ? 'Running' : 'Paused'}</span></div>
      </div>
      <div className="system-state__updated">
        <span>API updated</span>
        <strong>{timeAgo(health.updated_at)}</strong>
      </div>
    </section>
  )
}

function SourceStat({ label, count, detail }: { label: string; count: number; detail: string }) {
  return (
    <div className="system-state__item" title={detail}>
      <span className={`source-dot ${count ? 'is-active' : ''}`} />
      <div><strong>{label}</strong><span>{count ? `${formatNumber(count)} real events` : 'No real events'}</span></div>
    </div>
  )
}
