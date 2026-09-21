import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useSystem } from '../hooks/useApiQueries'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [health, jobs] = useSystem()
  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close navigation overlay" />}
      <div className="app-shell__body">
        <TopBar health={health.data} jobs={jobs.data} onMenu={() => setSidebarOpen(true)} />
        <main className="workspace"><Outlet /></main>
      </div>
    </div>
  )
}

