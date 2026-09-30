import { useMemo, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmotionBars } from '../charts/EmotionBars'
import { SentimentChart } from '../charts/SentimentChart'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { ErrorState, LoadingState } from '../components/States'
import { TimeRangeSelector, type TimeRange } from '../components/TimeRangeSelector'
import { useEmotions, useSentiment } from '../hooks/useApiQueries'
import { emotionTotals, filterTemporalRange } from '../utils/dashboard'
import { formatDateTime, formatPercent, sentenceCase } from '../utils/format'

export function SentimentPage() {
  const [range, setRange] = useState<TimeRange>('24H')
  const sentiment = useSentiment()
  const emotions = useEmotions()
  if (sentiment.isLoading || emotions.isLoading) return <LoadingState />
  if (sentiment.error || emotions.error) return <ErrorState error={sentiment.error ?? emotions.error} />
  const points = filterTemporalRange(sentiment.data?.rolling_1h ?? [], range)
  const emotionPoints = filterTemporalRange(emotions.data?.rolling_1h ?? [], range)
  const latest = points.at(-1)
  const stance = latest?.stance_distribution ?? {}
  return (
    <div className="page-stack">
      <PageHeader title="Sentiment & emotion" subtitle="Separate model signals aligned to source timestamps. These are model estimates, not confirmed feelings." actions={<TimeRangeSelector value={range} onChange={setRange} />} />
      <section className="signal-summary" aria-label="Latest sentiment and model signals">
        <div className="signal-summary__group"><span className="eyebrow">SENTIMENT</span><SignalValue label="Positive" value={formatPercent(latest?.positive_ratio ?? null)} tone="positive" /><SignalValue label="Neutral" value={formatPercent(latest?.neutral_ratio ?? null)} /><SignalValue label="Negative" value={formatPercent(latest?.negative_ratio ?? null)} tone="negative" /></div>
        <div className="signal-summary__group"><span className="eyebrow">MODEL SIGNALS</span><SignalValue label="Anxiety" value={formatPercent(latest?.anxiety_average ?? null)} detail="mapped from nervousness" /><SignalValue label="Irony" value={formatPercent(latest?.irony_rate ?? null)} detail="model estimate" /><SignalValue label="Volume" value={latest ? String(latest.event_count) : 'Unavailable'} detail="latest source window" /></div>
      </section>
      <Panel title="Sentiment Over Time" subtitle="Positive, neutral and negative remain distinct model outputs"><SentimentChart points={points} /></Panel>
      <div className="dashboard-grid">
        <Panel title="Emotion Distribution" subtitle="Fine-grained GoEmotions scores" className="span-5"><EmotionBars emotions={emotionTotals(emotionPoints)} /></Panel>
        <Panel title="Emotion Over Time" subtitle="Selected operational signals" className="span-7"><EmotionTimeline points={emotionPoints} /></Panel>
      </div>
      <div className="dashboard-grid">
        <Panel title="Stance Distribution" subtitle="Shown only when a validated fixed target exists" className="span-6">
          {Object.keys(stance).length ? <div className="distribution-list">{Object.entries(stance).map(([label, value]) => <div key={label}><span>{sentenceCase(label)}</span><div><i style={{ width: `${value * 100}%` }} /></div><b>{formatPercent(value)}</b></div>)}</div> : <div className="insight-callout insight-callout--neutral">General-target stance is unavailable. Sentiment is not substituted for stance.</div>}
        </Panel>
        <Panel title="Model Interpretation" subtitle="Evidence and limitations" className="span-6">
          <div className="insight-list"><p><b>Sentiment</b><span>CardiffNLP social-text classifier with positive, neutral and negative probabilities.</span></p><p><b>Emotion</b><span>GoEmotions multi-label scores. “Anxiety” is a product mapping from native nervousness.</span></p><p><b>Irony</b><span>Binary irony confidence is not equivalent to universal sarcasm understanding.</span></p></div>
        </Panel>
      </div>
    </div>
  )
}

function SignalValue({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone?: 'positive' | 'negative' }) {
  return <div className="signal-value"><span>{label}</span><strong className={tone ? `signal-value--${tone}` : ''}>{value}</strong>{detail && <small>{detail}</small>}</div>
}

function EmotionTimeline({ points }: { points: import('../types/analytics').TemporalPoint[] }) {
  const data = useMemo(() => points.map((point) => ({ ...point, anxiety: point.anxiety_average * 100, excitement: point.excitement_average * 100, irony: point.irony_rate * 100 })), [points])
  return (
    <div className="chart chart--bars"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ left: -20, right: 10, top: 8 }}><CartesianGrid stroke="#303234" vertical={false} /><XAxis dataKey="window_end" tickFormatter={(value) => formatDateTime(String(value)).split(',').at(-1) ?? ''} tick={{ fontSize: 12, fill: '#a1a3a5' }} axisLine={false} tickLine={false} /><YAxis tickFormatter={(value) => `${value}%`} tick={{ fontSize: 12, fill: '#a1a3a5' }} axisLine={false} tickLine={false} /><Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} labelFormatter={(value) => formatDateTime(String(value))} contentStyle={{ borderRadius: 12, borderColor: '#434547', background: '#1d1f21', color: '#f5f5f2' }} /><Legend iconType="circle" iconSize={7} /><Line dataKey="anxiety" stroke="#f2b957" strokeWidth={2} dot={false} /><Line dataKey="excitement" stroke="#f6de62" strokeWidth={2} dot={false} /><Line dataKey="irony" stroke="#a884d8" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>
  )
}
