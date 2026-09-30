import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState } from '../components/States'
import { sentenceCase } from '../utils/format'

export function EmotionBars({ emotions }: { emotions: Record<string, number> }) {
  const data = Object.entries(emotions)
    .sort(([, left], [, right]) => right - left)
    .slice(0, 8)
    .map(([emotion, score]) => ({ emotion: sentenceCase(emotion), score: score * 100 }))
  if (!data.length) return <EmptyState detail="Emotion scores are unavailable for this window." />
  return (
    <div className="chart chart--bars" aria-label="Emotion distribution chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 20, right: 12, top: 0, bottom: 0 }}>
          <CartesianGrid stroke="#303234" horizontal={false} />
          <XAxis type="number" domain={[0, 'auto']} hide />
          <YAxis type="category" dataKey="emotion" width={88} tick={{ fontSize: 12, fill: '#b4b6b7' }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Score']} contentStyle={{ borderRadius: 12, borderColor: '#434547', background: '#1d1f21', color: '#f5f5f2', fontSize: 13 }} />
          <Bar dataKey="score" fill="#f6de62" radius={[0, 5, 5, 0]} barSize={12} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
