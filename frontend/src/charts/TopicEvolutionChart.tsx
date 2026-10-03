import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState } from '../components/States'
import type { TopicEvolutionPoint } from '../types/analytics'
import { ChartTooltip } from './ChartTooltip'
import { axisProps, COLORS, fullTime, timeTickFormatter } from './theme'

export function TopicEvolutionChart({ points }: { points: TopicEvolutionPoint[] }) {
  if (points.length < 2) {
    return <EmptyState title="One measurement so far" detail="The evolution chart appears after a second matched window is measured." />
  }
  const data = points.map((point) => ({ t: new Date(point.window_end).getTime(), volume: point.volume }))
  const tick = timeTickFormatter(data)
  return (
    <div className="chart" role="img" aria-label={`Topic volume across ${data.length} windows`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 4, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="topic-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS.accent} stopOpacity={0.35} />
              <stop offset="100%" stopColor={COLORS.accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke={COLORS.line} />
          <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tick} minTickGap={36} {...axisProps} />
          <YAxis {...axisProps} width={44} allowDecimals={false} />
          <Tooltip content={<ChartTooltip labelFormatter={(label) => fullTime(Number(label))} valueFormatter={(n) => `${n} documents`} />} />
          <Area type="monotone" dataKey="volume" name="Volume" stroke={COLORS.accent} strokeWidth={1.75} fill="url(#topic-fill)" animationDuration={600} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
