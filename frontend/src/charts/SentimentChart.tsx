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
          <CartesianGrid stroke="#eef0f3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={(value) => formatDateTime(String(value)).split(',').at(-1) ?? ''} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
          <Tooltip
            labelFormatter={(value) => formatDateTime(String(value))}
            formatter={(value, name) => [`${Number(value).toFixed(1)}%`, String(name)]}
            contentStyle={{ borderRadius: 10, borderColor: '#eaecef', fontSize: 12 }}
          />
          <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="positive" stroke="#10b981" strokeWidth={2.3} dot={false} activeDot={{ r: 4 }} />
          <Line type="monotone" dataKey="neutral" stroke="#94a3b8" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="negative" stroke="#e11d48" strokeWidth={2.3} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

