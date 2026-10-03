import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getSentiment } from '../api/analytics'
import { getHealth } from '../api/system'
import { VolumeChart } from '../charts/VolumeChart'
import { AnimatedNumber } from '../components/AnimatedNumber'
import { platformLabel } from '../utils/platform'
import { selectSeries } from '../utils/dashboard'
import { timeAgo } from '../utils/format'

const SECTIONS = [
  { to: '/live-feed', title: 'Conversations', text: 'Every collected post, comment and reply, searchable and filterable by platform, sentiment, emotion and type.' },
  { to: '/sentiment', title: 'Sentiment', text: 'Positive, neutral and negative share, emotion scores and irony rate per time window.' },
  { to: '/trends', title: 'Topics', text: 'Topics discovered from the text itself, measured window by window for volume, growth and velocity.' },
  { to: '/network', title: 'Interaction map', text: 'Replies, mentions, quotes and forwards as a graph, with communities, central accounts and reply chains.' },
  { to: '/audience-lab', title: 'Audience Lab', text: 'Segments built from your audience data, one AI agent per segment, and a pre-flight test for drafts before you post.' },
  { to: '/data-sources', title: 'Sources', text: 'Add Telegram channels, YouTube videos or X queries. Collectors run on a schedule and store everything locally.' },
]

export function LandingPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 15_000 })
  const sentiment = useQuery({ queryKey: ['analytics', 'sentiment'], queryFn: getSentiment, refetchInterval: 60_000 })
  const platforms = (health.data?.platforms ?? []).filter((platform) => platform.real_event_count > 0)
  const newest = platforms.map((platform) => platform.latest_collected_at).filter(Boolean).sort().at(-1)
  const series = selectSeries(sentiment.data, '30d')
  const latest = series.at(-1)

  return (
    <div className="landing">
      <header className="landing__nav">
        <Link to="/" className="rail__brand" style={{ margin: 0 }}><img src="/logo.svg" alt="" /><span>Social Sentinel</span></Link>
        <Link to="/dashboard" className="btn btn--primary">Open dashboard <ArrowRight size={14} /></Link>
      </header>

      <main className="landing__main">
        <section className="landing__hero">
          <h1>Conversation analytics for X, Telegram and YouTube</h1>
          <p>Collects public posts and comments, scores sentiment, emotion and irony, finds topics, and maps who interacts with whom. The Audience Lab tests a draft against AI agents built from your own audience before it goes out.</p>
          <div className="landing__actions">
            <Link to="/dashboard" className="btn btn--primary">Open dashboard <ArrowRight size={14} /></Link>
            <Link to="/audience-lab" className="btn">Test a post</Link>
          </div>
        </section>

        <section className="landing__live" aria-label="Current data">
          <div className="landing__numbers">
            <div><span>Events stored</span><strong>{health.data ? <AnimatedNumber value={health.data.real_event_count} /> : '–'}</strong></div>
            <div><span>Platforms with data</span><strong>{health.data ? platforms.map((platform) => platformLabel(platform.platform)).join(', ') || 'None yet' : '–'}</strong></div>
            <div><span>Newest event collected</span><strong>{newest ? timeAgo(newest) : '–'}</strong></div>
            <div><span>Positive, latest day</span><strong className="pos">{latest ? `${(latest.positive_ratio * 100).toFixed(0)}%` : '–'}</strong></div>
          </div>
          <div className="landing__chart">
            {health.error ? <p className="muted">The API is not reachable. Start the backend to see live data.</p> : <VolumeChart points={series} height={220} />}
          </div>
          <p className="faint" style={{ fontSize: 12.5 }}>Live from this installation's database. Daily analysed events by sentiment, last 30 days of data.</p>
        </section>

        <section className="landing__sections">
          {SECTIONS.map((section) => (
            <Link key={section.to} to={section.to} className="landing__card">
              <h2>{section.title}<ArrowRight size={14} /></h2>
              <p>{section.text}</p>
            </Link>
          ))}
        </section>
      </main>

      <footer className="landing__footer faint">
        <span>Social Sentinel · runs locally, data stays in your PostgreSQL</span>
        <Link to="/collection-status">System status</Link>
      </footer>
    </div>
  )
}
