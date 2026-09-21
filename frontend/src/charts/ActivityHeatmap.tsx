import type { CanonicalEvent } from '../types/events'
import { buildHeatmap } from '../utils/dashboard'

const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const hours = ['12a', '3a', '6a', '9a', '12p', '3p', '6p', '9p']

export function ActivityHeatmap({ events }: { events: CanonicalEvent[] }) {
  const cells = buildHeatmap(events)
  return (
    <div className="heatmap" aria-label="Conversation activity by UTC day and three-hour interval">
      <div className="heatmap__corner">UTC</div>
      {hours.map((hour) => <div key={hour} className="heatmap__hour">{hour}</div>)}
      {days.map((day, dayIndex) => (
        <div className="heatmap__row" key={day}>
          <div className="heatmap__day">{day}</div>
          {cells.filter((cell) => cell.day === dayIndex).map((cell) => (
            <div
              key={`${cell.day}-${cell.hourBucket}`}
              className="heatmap__cell"
              style={{ '--intensity': Math.max(0.06, cell.intensity) } as React.CSSProperties}
              title={`${day} ${hours[cell.hourBucket]}: ${cell.count} events`}
              aria-label={`${day} ${hours[cell.hourBucket]}, ${cell.count} events`}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

