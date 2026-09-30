import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TemporalPoint } from '../types/analytics'
import { formatDateTime } from '../utils/format'
import { EmptyState } from '../components/States'

export function SentimentChart({ points }: { points: TemporalPoint[] }) {
  if (!points.length) return <EmptyState detail="Sentiment appears after NLP has processed events." />
  const data = points.map((point) => ({
    timestamp: point.window_end,
    positive: point.positive_ratio * 100,
    neutral: point.neutral_ratio * 100,
    negative: point.negative_ratio * 100,
    volume: point.event_count,
  }))
  return (
    <div className="chart chart--large" aria-label="Sentiment over time chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 8, bottom: 2, left: -20 }}>
          <CartesianGrid stroke="#303234" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={(value) => formatDateTime(String(value)).split(',').at(-1) ?? ''} tick={{ fontSize: 12, fill: '#a1a3a5' }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} tick={{ fontSize: 12, fill: '#a1a3a5' }} axisLine={false} tickLine={false} />
          <Tooltip
            labelFormatter={(value) => formatDateTime(String(value))}
            formatter={(value, name) => [`${Number(value).toFixed(1)}%`, String(name)]}
            contentStyle={{ borderRadius: 12, borderColor: '#434547', background: '#1d1f21', color: '#f5f5f2', fontSize: 13 }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="positive" stroke="#27cdb8" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
          <Line type="monotone" dataKey="neutral" stroke="#f6de62" strokeWidth={2.2} dot={false} />
          <Line type="monotone" dataKey="negative" stroke="#ff7a35" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
