import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { LoadingState } from '../components/States'
import { AppShell } from '../layouts/AppShell'

const OverviewPage = lazy(() => import('../pages/OverviewPage').then((module) => ({ default: module.OverviewPage })))
const LiveFeedPage = lazy(() => import('../pages/LiveFeedPage').then((module) => ({ default: module.LiveFeedPage })))
const SentimentPage = lazy(() => import('../pages/SentimentPage').then((module) => ({ default: module.SentimentPage })))
const TrendsPage = lazy(() => import('../pages/TrendsPage').then((module) => ({ default: module.TrendsPage })))
const TopicDetailPage = lazy(() => import('../pages/TopicDetailPage').then((module) => ({ default: module.TopicDetailPage })))
const NetworkPage = lazy(() => import('../pages/NetworkPage').then((module) => ({ default: module.NetworkPage })))
const TimelinePage = lazy(() => import('../pages/TimelinePage').then((module) => ({ default: module.TimelinePage })))
const DataSourcesPage = lazy(() => import('../pages/DataSourcesPage').then((module) => ({ default: module.DataSourcesPage })))
const DemographicsPage = lazy(() => import('../pages/DemographicsPage').then((module) => ({ default: module.DemographicsPage })))
const CollectionStatusPage = lazy(() => import('../pages/CollectionStatusPage').then((module) => ({ default: module.CollectionStatusPage })))
const UnavailablePage = lazy(() => import('../pages/UnavailablePage').then((module) => ({ default: module.UnavailablePage })))

export function App() {
  return (
    <Suspense fallback={<LoadingState />}><Routes>
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage />} />
        <Route path="live-feed" element={<LiveFeedPage />} />
        <Route path="sentiment" element={<SentimentPage />} />
        <Route path="trends" element={<TrendsPage />} />
        <Route path="trends/:topicId" element={<TopicDetailPage />} />
        <Route path="network" element={<NetworkPage />} />
        <Route path="demographics" element={<DemographicsPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="data-sources" element={<DataSourcesPage />} />
        <Route path="collection-status" element={<CollectionStatusPage />} />
        <Route path="settings" element={<UnavailablePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes></Suspense>
  )
}
