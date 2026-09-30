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
          <CartesianGrid stroke="#303234" vertical={false} />
          <XAxis dataKey="window_start" tickFormatter={(value) => formatDateTime(String(value)).split(',').at(-1) ?? ''} tick={{ fontSize: 12, fill: '#a1a3a5' }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#a1a3a5' }} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={(value) => formatDateTime(String(value))} contentStyle={{ borderRadius: 12, borderColor: '#434547', background: '#1d1f21', color: '#f5f5f2', fontSize: 13 }} />
          <Line dataKey="volume" name="Volume" stroke="#f6de62" strokeWidth={2.5} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
