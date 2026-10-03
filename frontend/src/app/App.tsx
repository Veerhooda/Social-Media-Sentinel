import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { LoadingState } from '../components/States'
import { AppShell } from '../layouts/AppShell'

const page = <T extends Record<string, React.ComponentType>>(load: () => Promise<T>, name: keyof T) =>
  lazy(() => load().then((module) => ({ default: module[name] })))

const LandingPage = page(() => import('../pages/LandingPage'), 'LandingPage')
const OverviewPage = page(() => import('../pages/OverviewPage'), 'OverviewPage')
const LiveFeedPage = page(() => import('../pages/LiveFeedPage'), 'LiveFeedPage')
const SentimentPage = page(() => import('../pages/SentimentPage'), 'SentimentPage')
const TrendsPage = page(() => import('../pages/TrendsPage'), 'TrendsPage')
const TopicDetailPage = page(() => import('../pages/TopicDetailPage'), 'TopicDetailPage')
const NetworkPage = page(() => import('../pages/NetworkPage'), 'NetworkPage')
const TimelinePage = page(() => import('../pages/TimelinePage'), 'TimelinePage')
const DataSourcesPage = page(() => import('../pages/DataSourcesPage'), 'DataSourcesPage')
const DemographicsPage = page(() => import('../pages/DemographicsPage'), 'DemographicsPage')
const AudienceLabPage = page(() => import('../pages/AudienceLabPage'), 'AudienceLabPage')
const CollectionStatusPage = page(() => import('../pages/CollectionStatusPage'), 'CollectionStatusPage')

const fallback = <div className="page"><LoadingState /></div>

export function App() {
  return (
    <Suspense fallback={fallback}>
      <Routes>
        <Route index element={<LandingPage />} />
        <Route element={<AppShell />}>
          <Route path="dashboard" element={<Suspense fallback={fallback}><OverviewPage /></Suspense>} />
          <Route path="live-feed" element={<Suspense fallback={fallback}><LiveFeedPage /></Suspense>} />
          <Route path="sentiment" element={<Suspense fallback={fallback}><SentimentPage /></Suspense>} />
          <Route path="trends" element={<Suspense fallback={fallback}><TrendsPage /></Suspense>} />
          <Route path="trends/:topicId" element={<Suspense fallback={fallback}><TopicDetailPage /></Suspense>} />
          <Route path="network" element={<Suspense fallback={fallback}><NetworkPage /></Suspense>} />
          <Route path="demographics" element={<Suspense fallback={fallback}><DemographicsPage /></Suspense>} />
          <Route path="audience-lab" element={<Suspense fallback={fallback}><AudienceLabPage /></Suspense>} />
          <Route path="timeline" element={<Suspense fallback={fallback}><TimelinePage /></Suspense>} />
          <Route path="data-sources" element={<Suspense fallback={fallback}><DataSourcesPage /></Suspense>} />
          <Route path="collection-status" element={<Suspense fallback={fallback}><CollectionStatusPage /></Suspense>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
