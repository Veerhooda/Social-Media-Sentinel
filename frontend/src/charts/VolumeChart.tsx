import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState } from '../components/States'
import type { TemporalPoint } from '../types/analytics'
import { ChartTooltip } from './ChartTooltip'
import { axisProps, COLORS, fullTime, timeTickFormatter } from './theme'

const SERIES = [
  { key: 'positive', label: 'Positive', color: COLORS.pos },
  { key: 'neutral', label: 'Neutral', color: COLORS.neu },
  { key: 'negative', label: 'Negative', color: COLORS.neg },
] as const

/**
 * Sentiment-split event volume per measured window.
 * `share` plots the proportions (stacked to 100%); `count` plots analysed events.
 */
export function VolumeChart({ points, mode = 'count', height = 280 }: { points: TemporalPoint[]; mode?: 'count' | 'share'; height?: number }) {
  if (points.length < 2) {
    return <EmptyState title={points.length ? 'One measured window so far' : 'No analysed events in this range'} detail="A chart appears once at least two windows contain analysed events." />
  }
  const data = points.map((point) => {
    const scale = mode === 'count' ? point.event_count : 100
    return {
      t: new Date(point.window_end).getTime(),
      events: point.event_count,
      positive: point.positive_ratio * scale,
      neutral: point.neutral_ratio * scale,
      negative: point.negative_ratio * scale,
    }
  })
  const tick = timeTickFormatter(data)
  const value = (n: number) => (mode === 'share' ? `${n.toFixed(1)}%` : Math.round(n).toLocaleString('en'))
  return (
    <div className="chart" style={{ height }} role="img" aria-label={`${mode === 'share' ? 'Sentiment share' : 'Analysed event volume by sentiment'} across ${data.length} windows`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 4, bottom: 0, left: -18 }}>
          <defs>
            {SERIES.map((series) => (
              <linearGradient key={series.key} id={`fill-${series.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={series.color} stopOpacity={0.5} />
                <stop offset="100%" stopColor={series.color} stopOpacity={0.12} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid vertical={false} stroke={COLORS.line} />
          <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tick} minTickGap={36} {...axisProps} />
          <YAxis {...axisProps} width={44} domain={mode === 'share' ? [0, 100] : [0, 'auto']} tickFormatter={(n) => (mode === 'share' ? `${n}%` : String(n))} allowDecimals={false} />
          <Tooltip cursor={{ stroke: COLORS.text3, strokeDasharray: '3 3' }} content={<ChartTooltip labelFormatter={(label) => fullTime(Number(label))} valueFormatter={(n) => value(n)} />} />
          {SERIES.map((series) => (
            <Area key={series.key} type="monotone" dataKey={series.key} name={series.label} stackId="s" stroke={series.color} strokeWidth={1.5} fill={`url(#fill-${series.key})`} animationDuration={600} />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function SentimentLegend() {
  return <div className="legend">{SERIES.map((series) => <span key={series.key}><i className="dot" style={{ background: series.color }} />{series.label}</span>)}</div>
}
