import {
  Activity,
  Bot,
  ChartLine,
  Clock3,
  DatabaseZap,
  GitBranch,
  LayoutDashboard,
  MessagesSquare,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const sections = [
  {
    label: 'Analyze',
    items: [
      ['Overview', '/dashboard', LayoutDashboard],
      ['Conversations', '/live-feed', MessagesSquare],
      ['Sentiment', '/sentiment', ChartLine],
      ['Topics', '/trends', TrendingUp],
      ['Interaction map', '/network', GitBranch],
      ['Timeline', '/timeline', Clock3],
    ],
  },
  {
    label: 'Audience',
    items: [
      ['Demographics', '/demographics', Users],
      ['Audience Lab', '/audience-lab', Bot],
    ],
  },
  {
    label: 'Collection',
    items: [
      ['Sources', '/data-sources', DatabaseZap],
      ['Jobs', '/collection-status', Activity],
    ],
  },
] as const

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <aside className={`rail ${open ? 'is-open' : ''}`} aria-label="Primary">
      <div className="rail__brand">
        <img src="/logo.svg" alt="" />
        <span>Social Sentinel</span>
        <button type="button" className="rail__close" onClick={onClose} aria-label="Close navigation"><X size={16} /></button>
      </div>
      <nav>
        {sections.map((section) => (
          <div className="rail__group" key={section.label}>
            <span className="rail__label">{section.label}</span>
            {section.items.map(([label, to, Icon]) => (
              <NavLink key={to} to={to} end={to === '/dashboard'} className={({ isActive }) => `rail__link ${isActive ? 'is-active' : ''}`}>
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  )
}
