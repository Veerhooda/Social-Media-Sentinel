import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState } from '../components/States'
import type { TemporalPoint } from '../types/analytics'
import { ChartTooltip } from './ChartTooltip'
import { axisProps, COLORS, fullTime, timeTickFormatter } from './theme'

const SERIES = [
  { key: 'irony', label: 'Irony rate', color: COLORS.sar },
  { key: 'anxiety', label: 'Anxiety', color: COLORS.neg },
  { key: 'excitement', label: 'Excitement', color: COLORS.accent },
] as const

export function SignalChart({ points }: { points: TemporalPoint[] }) {
  if (points.length < 2) return <EmptyState title="Not enough windows" detail="At least two analysed windows are needed." />
  const data = points.map((point) => ({
    t: new Date(point.window_end).getTime(),
    irony: point.irony_rate * 100,
    anxiety: point.anxiety_average * 100,
    excitement: point.excitement_average * 100,
  }))
  const tick = timeTickFormatter(data)
  return (
    <>
      <div className="chart chart--sm" role="img" aria-label="Irony, anxiety and excitement over time">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 4, bottom: 0, left: -18 }}>
            <CartesianGrid vertical={false} stroke={COLORS.line} />
            <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tick} minTickGap={36} {...axisProps} />
            <YAxis {...axisProps} width={44} tickFormatter={(n) => `${n}%`} />
            <Tooltip content={<ChartTooltip labelFormatter={(label) => fullTime(Number(label))} valueFormatter={(n) => `${n.toFixed(1)}%`} />} />
            {SERIES.map((series) => <Line key={series.key} type="monotone" dataKey={series.key} name={series.label} stroke={series.color} strokeWidth={1.75} dot={false} activeDot={{ r: 3 }} animationDuration={600} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="legend" style={{ marginTop: 10 }}>{SERIES.map((series) => <span key={series.key}><i className="dot" style={{ background: series.color }} />{series.label}</span>)}</div>
    </>
  )
}
