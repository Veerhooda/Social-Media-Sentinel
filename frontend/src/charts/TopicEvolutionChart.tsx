import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { TopicEvolutionPoint } from '../types/analytics'
import { EmptyState } from '../components/States'
import { formatDateTime } from '../utils/format'

export function TopicEvolutionChart({ points }: { points: TopicEvolutionPoint[] }) {
  if (points.length < 2) {
    return <EmptyState title="Insufficient data for temporal evolution" detail="At least two matched source-time measurements are required." />
  }
  return (
    <div className="chart chart--medium" aria-label="Topic volume evolution chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ left: -20, right: 12, top: 8, bottom: 4 }}>
          <CartesianGrid stroke="#eef0f3" vertical={false} />
          <XAxis dataKey="window_start" tickFormatter={(value) => formatDateTime(String(value)).split(',').at(-1) ?? ''} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={(value) => formatDateTime(String(value))} contentStyle={{ borderRadius: 10, borderColor: '#eaecef', fontSize: 12 }} />
          <Line dataKey="volume" name="Volume" stroke="#ff7a00" strokeWidth={2.4} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

