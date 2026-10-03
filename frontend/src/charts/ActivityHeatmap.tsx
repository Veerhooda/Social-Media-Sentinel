import type { CanonicalEvent } from '../types/events'
import { buildHeatmap } from '../utils/dashboard'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const HOURS = ['00', '03', '06', '09', '12', '15', '18', '21']

/** Posting activity by UTC weekday and 3-hour block, from the events passed in. */
export function ActivityHeatmap({ events }: { events: CanonicalEvent[] }) {
  const cells = buildHeatmap(events)
  return (
    <div className="heatmap" role="table" aria-label="Posting activity by UTC day and three-hour block">
      <span role="columnheader">UTC</span>
      {HOURS.map((hour) => <span key={hour} role="columnheader">{hour}</span>)}
      {DAYS.map((day, dayIndex) => (
        <div key={day} role="row" style={{ display: 'contents' }}>
          <span role="rowheader">{day}</span>
          {cells.filter((cell) => cell.day === dayIndex).map((cell) => (
            <i
              key={`${cell.day}-${cell.hourBucket}`}
              role="cell"
              data-empty={cell.count === 0}
              style={{ opacity: cell.count ? 0.18 + cell.intensity * 0.82 : 1 }}
              title={`${day} ${HOURS[cell.hourBucket]}:00 UTC · ${cell.count} events`}
              aria-label={`${day} ${HOURS[cell.hourBucket]}:00, ${cell.count} events`}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
