import {
  Activity,
  ChartLine,
  Clock3,
  DatabaseZap,
  GitBranch,
  LayoutDashboard,
  RadioTower,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const sections = [
  {
    label: 'MAIN',
    items: [
      ['Overview', '/dashboard', LayoutDashboard],
      ['Conversation Feed', '/live-feed', RadioTower],
      ['Sentiment & Emotion', '/sentiment', ChartLine],
      ['Trends & Topics', '/trends', TrendingUp],
      ['Interaction Map', '/network', GitBranch],
      ['Demographics', '/demographics', Users],
      ['Timeline', '/timeline', Clock3],
    ],
  },
  {
    label: 'DATA',
    items: [
      ['Data Sources', '/data-sources', DatabaseZap],
      ['Collection Status', '/collection-status', Activity],
    ],
  },
] as const

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <div className="brand">
        <span className="brand__mark"><img src="/favicon.svg" alt="" /></span>
        <div><strong>Social Sentinel</strong><span>Audience intelligence</span></div>
        <button type="button" className="sidebar__close" onClick={onClose} aria-label="Close navigation"><X size={18} /></button>
      </div>
      <nav aria-label="Primary navigation">
        {sections.map((section) => (
          <div className="nav-section" key={section.label}>
            <span className="nav-section__label">{section.label}</span>
            {section.items.map(([label, to, Icon]) => (
              <NavLink key={to} to={to} end={to === '/dashboard'} className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`} onClick={onClose}>
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar__footer">
        <NavLink to="/collection-status" className="sidebar__signal"><Activity size={16} /><span>System status</span></NavLink>
        <div className="sidebar__profile"><span className="sidebar__profile-mark">SS</span><div><strong>Research workspace</strong><span>Source-time analysis</span></div></div>
      </div>
    </aside>
  )
}
