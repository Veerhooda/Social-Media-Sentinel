import {
  Activity,
  ChartLine,
  CircleUserRound,
  Clock3,
  DatabaseZap,
  Gauge,
  GitBranch,
  LayoutDashboard,
  RadioTower,
  Settings,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const sections = [
  {
    label: 'MAIN',
    items: [
      ['Overview', '/', LayoutDashboard],
      ['Live Feed', '/live-feed', RadioTower],
      ['Sentiment & Emotion', '/sentiment', ChartLine],
      ['Trends & Topics', '/trends', TrendingUp],
      ['Network Analysis', '/network', GitBranch],
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
  {
    label: 'SYSTEM',
    items: [['Settings', '/settings', Settings]],
  },
] as const

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <div className="brand">
        <span className="brand__mark"><Gauge size={21} strokeWidth={2.2} /></span>
        <div><strong>Social Sentinel</strong><span>Intelligence Console</span></div>
        <button type="button" className="sidebar__close" onClick={onClose} aria-label="Close navigation"><X size={18} /></button>
      </div>
      <nav aria-label="Primary navigation">
        {sections.map((section) => (
          <div className="nav-section" key={section.label}>
            <span className="nav-section__label">{section.label}</span>
            {section.items.map(([label, to, Icon]) => (
              <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`} onClick={onClose}>
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar__footer">
        <NavLink to="/collection-status" className="sidebar__signal"><Activity size={16} /><span>System status</span></NavLink>
        <div className="sidebar__profile"><CircleUserRound size={30} /><div><strong>Analyst</strong><span>Local workspace</span></div></div>
      </div>
    </aside>
  )
}
