import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function AppShell() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  useEffect(() => { setOpen(false); window.scrollTo?.({ top: 0 }) }, [location.pathname])
  return (
    <div className="shell">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      {open && <button type="button" className="rail-backdrop" onClick={() => setOpen(false)} aria-label="Close navigation" />}
      <div className="shell__main">
        <TopBar onMenu={() => setOpen(true)} />
        <main className="workspace" id="main">
          <Outlet key={location.pathname} />
        </main>
      </div>
    </div>
  )
}
