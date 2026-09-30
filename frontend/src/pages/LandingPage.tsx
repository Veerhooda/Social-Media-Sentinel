import { ArrowDown, ArrowUpRight, BarChart3, GitBranch, Menu, MessageCircle, Radar, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ScrollRose } from '../components/ScrollRose'
import './landing.css'

const capabilities = [
  { number: '01', icon: MessageCircle, title: 'Read the room.', detail: 'Track sentiment, fine-grained emotion, and irony across the conversations you collect.' },
  { number: '02', icon: Radar, title: 'See what is taking shape.', detail: 'Discover topics, compare source-time windows, and distinguish a signal from insufficient history.' },
  { number: '03', icon: GitBranch, title: 'Follow the connections.', detail: 'Explore observed replies, mentions, quotes, and forwards without inventing a follower network.' },
]

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="landing">
      <header className="landing-nav-wrap">
        <nav className="landing-nav" aria-label="Landing navigation">
          <Link className="landing-brand" to="/" aria-label="Social Sentinel home">
            <img src="/favicon.svg" alt="" />
            <span>social<span className="landing-brand__period">.</span>sentinel</span>
          </Link>
          <div className={`landing-nav__links ${menuOpen ? 'is-open' : ''}`}>
            <a href="#platform" onClick={() => setMenuOpen(false)}>Platform</a>
            <a href="#capabilities" onClick={() => setMenuOpen(false)}>Capabilities</a>
            <Link to="/dashboard" onClick={() => setMenuOpen(false)}>Dashboard <ArrowUpRight size={16} aria-hidden="true" /></Link>
          </div>
          <button className="landing-nav__toggle" type="button" aria-expanded={menuOpen} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} onClick={() => setMenuOpen((open) => !open)}>
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </nav>
      </header>

      <main>
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-hero__eyebrow"><span className="landing-pulse" /> A clearer view of public conversation</div>
          <h1 id="landing-title">The conversation<br /> beneath the <span>conversation.</span></h1>
          <p className="landing-hero__subtitle">Turn collected social activity into a source-grounded picture of what people feel, what narratives are forming, and how information moves.</p>
          <div className="landing-hero__actions">
            <Link className="landing-cta landing-cta--primary" to="/dashboard">Enter the dashboard <span><ArrowUpRight size={22} aria-hidden="true" /></span></Link>
            <a className="landing-cta landing-cta--quiet" href="#platform">Explore the platform <ArrowDown size={17} aria-hidden="true" /></a>
          </div>

          <div className="landing-showcase" aria-label="Illustrative previews of Social Sentinel analytics">
            <div className="landing-showcase__column">
              <Link to="/trends" className="landing-preview landing-preview--topic">
                <div className="landing-preview__top"><span>01 / TOPIC EVOLUTION</span><Radar size={20} aria-hidden="true" /></div>
                <div className="landing-preview__plot" aria-hidden="true"><svg viewBox="0 0 420 170" preserveAspectRatio="none"><defs><linearGradient id="landing-topic-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#f6de62" stopOpacity=".38"/><stop offset="1" stopColor="#f6de62" stopOpacity="0"/></linearGradient></defs><path d="M0 145 L47 140 L82 132 L116 136 L156 114 L196 112 L225 95 L262 102 L300 67 L336 72 L371 35 L420 17 L420 170 L0 170Z" fill="url(#landing-topic-fill)"/><path d="M0 145 L47 140 L82 132 L116 136 L156 114 L196 112 L225 95 L262 102 L300 67 L336 72 L371 35 L420 17" fill="none" stroke="#f6de62" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg></div>
                <div className="landing-preview__overlay"><strong>Patterns, not noise.</strong><p>See topics change across source-time windows.</p><span>Explore topic evolution <ArrowUpRight size={16} aria-hidden="true" /></span></div>
              </Link>
              <Link to="/network" className="landing-preview landing-preview--network">
                <div className="landing-preview__top"><span>02 / INTERACTION MAP</span><GitBranch size={20} aria-hidden="true" /></div>
                <div className="landing-network-art" aria-hidden="true"><span className="landing-network-art__hub" /><span className="landing-network-art__node a" /><span className="landing-network-art__node b" /><span className="landing-network-art__node c" /><span className="landing-network-art__node d" /></div>
                <div className="landing-preview__overlay"><strong>Follow the connections.</strong><p>Explore observed relationships, not imagined influence.</p><span>Open interaction map <ArrowUpRight size={16} aria-hidden="true" /></span></div>
              </Link>
            </div>
            <Link to="/dashboard" className="landing-showcase__feature">
              <div className="landing-feature__image" aria-hidden="true" />
              <div className="landing-feature__top"><img src="/favicon.svg" alt="" /><span>SOCIAL SENTINEL / ANALYTICS</span></div>
              <div className="landing-feature__content"><span>FROM POSTS TO PERSPECTIVE</span><strong>Understand more.<br /><em>Assume less.</em></strong><p>One workspace for source-grounded audience intelligence.</p></div>
              <div className="landing-feature__bottom"><span>Explore the intelligence workspace</span><ArrowUpRight size={24} aria-hidden="true" /></div>
            </Link>
          </div>
          <div className="landing-hero__tail"><span>DESIGNED FOR EVIDENCE, NOT GUESSWORK</span><span>SCROLL TO EXPLORE <ArrowDown size={15} aria-hidden="true" /></span></div>
        </section>

        <ScrollRose />

        <section className="landing-section landing-section--intro" id="platform" aria-labelledby="platform-title">
          <span className="landing-section__label">THE PLATFORM <span>01 / 02</span></span>
          <h2 id="platform-title">Make sense of the <span>whole conversation.</span></h2>
          <p>Social Sentinel connects canonical events, chronological analysis, and observed interactions in one workspace. Every claim is tied to collected data, with uncertainty shown when evidence is thin.</p>
          <Link className="landing-text-link" to="/dashboard">See it in action <ArrowUpRight size={19} aria-hidden="true" /></Link>
        </section>

        <section className="landing-section landing-section--capabilities" id="capabilities" aria-labelledby="capabilities-title">
          <span className="landing-section__label">WHAT YOU CAN EXPLORE <span>02 / 02</span></span>
          <h2 id="capabilities-title">Signals with <span>context.</span></h2>
          <div className="landing-capabilities">
            {capabilities.map(({ number, icon: Icon, title, detail }) => <article key={number} className="landing-capability"><span>{number} / 03</span><Icon size={26} strokeWidth={1.6} aria-hidden="true" /><h3>{title}</h3><p>{detail}</p></article>)}
          </div>
        </section>

        <section className="landing-final" aria-labelledby="landing-final-title"><span>YOUR INTELLIGENCE WORKSPACE IS READY</span><h2 id="landing-final-title">Look closer.</h2><Link className="landing-cta landing-cta--primary" to="/dashboard">Open dashboard <span><ArrowUpRight size={22} aria-hidden="true" /></span></Link></section>
      </main>

      <footer className="landing-footer"><div className="landing-brand"><img src="/favicon.svg" alt="" /><span>social<span className="landing-brand__period">.</span>sentinel</span></div><p>Source-grounded social intelligence.</p><Link to="/dashboard">Dashboard <BarChart3 size={17} aria-hidden="true" /></Link></footer>
    </div>
  )
}
