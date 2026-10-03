/** Mirrors styles/tokens.css for libraries that need literal colours (Recharts, Sigma). */
export const COLORS = {
  text: '#ecedee',
  text2: '#a9aeb5',
  text3: '#7c838c',
  line: '#24272c',
  surface: '#15171a',
  accent: '#e9c46a',
  pos: '#3fb98a',
  neu: '#8a9199',
  neg: '#e5594f',
  sar: '#ef8a3b',
} as const

export const CATEGORICAL = ['#e9c46a', '#3fb98a', '#ef8a3b', '#c9b8a0', '#5fb3a7', '#d9798d', '#9db35a', '#8a9199'] as const

export const SENTIMENT_COLORS: Record<string, string> = {
  positive: COLORS.pos,
  neutral: COLORS.neu,
  negative: COLORS.neg,
  sarcastic: COLORS.sar,
}

export const axisProps = {
  axisLine: false,
  tickLine: false,
  tick: { fill: COLORS.text3, fontSize: 11.5 },
} as const

export function timeTickFormatter(points: { t: number }[]) {
  const span = points.length > 1 ? points[points.length - 1].t - points[0].t : 0
  const longRange = span > 2 * 86_400_000
  const format = new Intl.DateTimeFormat('en', longRange ? { month: 'short', day: 'numeric' } : { hour: '2-digit', minute: '2-digit', hour12: false })
  return (value: number) => format.format(new Date(value))
}

export const fullTime = (value: number | string) =>
  new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value))
