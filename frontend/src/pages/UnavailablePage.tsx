import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { UnavailableState } from '../components/States'

export function UnavailablePage() {
  return <div className="page-stack"><PageHeader title="Settings" subtitle="Application and analytical configuration." /><Panel><UnavailableState title="Settings UI is not implemented" detail="Configuration remains environment-driven; credentials are never exposed in the dashboard." /></Panel></div>
}
