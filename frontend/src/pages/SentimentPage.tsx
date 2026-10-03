import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { getEnrichedEvents } from '../api/events'
import { SignalChart } from '../charts/SignalChart'
import { SentimentLegend, VolumeChart } from '../charts/VolumeChart'
import { Bars } from '../components/Bars'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Segmented } from '../components/Segmented'
import { Delta, Stat, Stats } from '../components/Stat'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { useEmotions, useSentiment } from '../hooks/useApiQueries'
import { bestRange, emotionTotals, SERIES_RANGES, selectSeries, splitNeutralEmotion, type SeriesRange } from '../utils/dashboard'
import { pct, sentenceCase } from '../utils/format'

export function SentimentPage() {
  const [chosen, setRange] = useState<SeriesRange | null>(null)
  const sentiment = useSentiment()
  const range = chosen ?? bestRange(sentiment.data, ['7d', '30d', 'all'])
  const emotions = useEmotions()
  const sample = useQuery({ queryKey: ['events', 'enriched', 'model-sample'], queryFn: () => getEnrichedEvents({ limit: 1, newest_first: true }) })
  const points = useMemo(() => selectSeries(sentiment.data, range), [sentiment.data, range])
  const emotionPoints = useMemo(() => selectSeries(emotions.data, range), [emotions.data, range])

  if (sentiment.isLoading || emotions.isLoading) return <div className="page"><LoadingState label="Loading sentiment" /></div>
  if (sentiment.error || emotions.error) return <div className="page"><ErrorState error={sentiment.error ?? emotions.error} /></div>

  const latest = points.at(-1)
  const previous = points.at(-2)
  const change = (key: 'positive_ratio' | 'neutral_ratio' | 'negative_ratio' | 'irony_rate' | 'anxiety_average') =>
    latest && previous ? (latest[key] - previous[key]) * 100 : null
  const analysed = points.reduce((sum, point) => sum + point.event_count, 0)
  // Average the emotion scores across every window in range, weighted by window size.
  const emotionAverage = ((): Record<string, number> => {
    const totals: Record<string, number> = {}
    let weight = 0
    emotionPoints.forEach((point) => {
      weight += point.event_count
      Object.entries(point.emotion_distribution).forEach(([label, value]) => { totals[label] = (totals[label] ?? 0) + value * point.event_count })
    })
    return weight ? Object.fromEntries(Object.entries(totals).map(([label, value]) => [label, value / weight])) : {}
  })()
  const { neutral, emotions: emotionScores } = splitNeutralEmotion(emotionTotals([{ ...(emotionPoints.at(-1) ?? emptyPoint), emotion_distribution: emotionAverage }]))
  const emotionItems = Object.entries(emotionScores)
    .map(([label, value]) => ({ label: label === 'anxiety' ? 'Anxiety' : sentenceCase(label), value, display: pct(value) }))
  const stance = latest?.stance_distribution ?? {}
  const models = sample.data?.items[0]?.analysis

  return (
    <div className="page">
      <PageHeader
        title="Sentiment"
        description={`${analysed.toLocaleString('en')} analysed events in ${points.length} ${range === '24h' ? 'hourly' : 'daily'} windows`}
        actions={<Segmented label="Time range" value={range} options={SERIES_RANGES} onChange={setRange} />}
      />
      <Stats label="Latest window">
        <Stat label="Positive" tone="pos" value={latest ? latest.positive_ratio * 100 : null} format={(n) => n.toFixed(1)} unit="%" meta={<Delta value={change('positive_ratio')} />} />
        <Stat label="Neutral" value={latest ? latest.neutral_ratio * 100 : null} format={(n) => n.toFixed(1)} unit="%" meta={<Delta value={change('neutral_ratio')} />} />
        <Stat label="Negative" tone="neg" value={latest ? latest.negative_ratio * 100 : null} format={(n) => n.toFixed(1)} unit="%" meta={<Delta value={change('negative_ratio')} invert />} />
        <Stat label="Irony rate" tone="sar" value={latest ? latest.irony_rate * 100 : null} format={(n) => n.toFixed(1)} unit="%" meta={<Delta value={change('irony_rate')} invert />} />
        <Stat label="Anxiety" value={latest ? latest.anxiety_average * 100 : null} format={(n) => n.toFixed(1)} unit="%" meta={<Delta value={change('anxiety_average')} invert />} />
        <Stat label="Events in window" value={latest?.event_count ?? null} meta={latest ? new Date(latest.window_end).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : undefined} />
      </Stats>

      <Panel title="Sentiment share" description="Share of analysed events per window" footer={<SentimentLegend />}>
        <VolumeChart points={points} mode="share" height={300} />
      </Panel>

      <div className="grid">
        <Panel className="col-5" title="Emotions" description={`Average score across the selected range${neutral != null ? ` · neutral ${pct(neutral, 0)}` : ''}`}>
          {emotionItems.length ? <Bars label="Emotion scores" items={emotionItems} /> : <EmptyState title="No emotion scores in this range" />}
        </Panel>
        <Panel className="col-7" title="Signals over time" description="Irony rate and average anxiety and excitement scores">
          <SignalChart points={points} />
        </Panel>
        {Object.keys(stance).length > 0 && (
          <Panel className="col-6" title="Stance" description={`Fixed-target stance, latest window`}>
            <Bars label="Stance distribution" items={Object.entries(stance).map(([label, value]) => ({ label: sentenceCase(label), value, display: pct(value) }))} max={1} />
          </Panel>
        )}
      </div>

      {models && (
        <p className="faint" style={{ fontSize: 12.5 }}>
          Models: {models.sentiment.model_name} (sentiment), {models.emotions.model_name} (emotion), {models.irony.model_name} (irony).
          Anxiety is the GoEmotions “nervousness” label.
        </p>
      )}
    </div>
  )
}

const emptyPoint = {
  window_start: '', window_end: '', event_count: 0, positive_ratio: 0, neutral_ratio: 0, negative_ratio: 0,
  emotion_distribution: {}, anxiety_average: 0, excitement_average: 0, irony_rate: 0, stance_distribution: {},
}
