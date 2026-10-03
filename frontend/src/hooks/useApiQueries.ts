import { keepPreviousData, queryOptions, useQueries, useQuery } from '@tanstack/react-query'
import { getDemographics, getEmotions, getSentiment, getTopics, getTrends } from '../api/analytics'
import { getEnrichedEvents, getEvents, getLiveEvents } from '../api/events'
import type { EventQuery } from '../api/events'
import {
  getNetworkCascade,
  getNetworkCascades,
  getNetworkCommunities,
  getNetworkGraph,
  getNetworkInfluence,
  getNetworkSummary,
  getNetworkTemporal,
} from '../api/network'
import { getHealth, getJobs } from '../api/system'

export const POLL_INTERVAL = 30_000
export const SYSTEM_POLL_INTERVAL = 10_000
export const LIVE_POLL_INTERVAL = 5_000

export const queryKeys = {
  health: ['health'] as const,
  jobs: ['jobs'] as const,
  events: (offset = 0) => ['events', offset] as const,
  enrichedEvents: (query: EventQuery = {}) => ['events', 'enriched', query] as const,
  liveEvents: ['events', 'live'] as const,
  sentiment: ['analytics', 'sentiment'] as const,
  emotions: ['analytics', 'emotions'] as const,
  trends: ['analytics', 'trends'] as const,
  topics: ['analytics', 'topics'] as const,
  demographics: ['analytics', 'demographics'] as const,
  networkSummary: ['network', 'summary'] as const,
  networkGraph: ['network', 'graph'] as const,
  networkTemporal: (window: string) => ['network', 'temporal', window] as const,
  networkInfluence: ['network', 'influence'] as const,
  networkCommunities: ['network', 'communities'] as const,
  networkCascades: ['network', 'cascades'] as const,
  networkCascade: (id: string) => ['network', 'cascade', id] as const,
}

export const healthQuery = queryOptions({
  queryKey: queryKeys.health,
  queryFn: getHealth,
  refetchInterval: SYSTEM_POLL_INTERVAL,
})

export const jobsQuery = queryOptions({
  queryKey: queryKeys.jobs,
  queryFn: getJobs,
  refetchInterval: SYSTEM_POLL_INTERVAL,
})

export function useOverviewData() {
  return useQueries({
    queries: [
      healthQuery,
      jobsQuery,
      queryOptions({
        queryKey: queryKeys.events(0),
        queryFn: () => getEvents({ limit: 250, newest_first: true }),
        refetchInterval: POLL_INTERVAL,
      }),
      queryOptions({
        queryKey: queryKeys.enrichedEvents({ limit: 12, newest_first: true }),
        queryFn: () => getEnrichedEvents({ limit: 12, newest_first: true }),
        refetchInterval: LIVE_POLL_INTERVAL,
      }),
      queryOptions({ queryKey: queryKeys.sentiment, queryFn: getSentiment, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.emotions, queryFn: getEmotions, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.trends, queryFn: getTrends, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.networkSummary, queryFn: getNetworkSummary, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.networkGraph, queryFn: () => getNetworkGraph(250), refetchInterval: POLL_INTERVAL }),
    ],
  })
}

export const useEnrichedEvents = (query: EventQuery = {}) =>
  useQuery({
    queryKey: queryKeys.enrichedEvents(query),
    queryFn: () => getEnrichedEvents({ limit: 50, newest_first: true, ...query }),
    placeholderData: keepPreviousData,
    refetchInterval: LIVE_POLL_INTERVAL,
  })

export const useLiveEvents = () =>
  useQuery({ queryKey: queryKeys.liveEvents, queryFn: () => getLiveEvents(25), refetchInterval: LIVE_POLL_INTERVAL })

export const useSentiment = () =>
  useQuery({ queryKey: queryKeys.sentiment, queryFn: getSentiment, refetchInterval: POLL_INTERVAL })

export const useEmotions = () =>
  useQuery({ queryKey: queryKeys.emotions, queryFn: getEmotions, refetchInterval: POLL_INTERVAL })

export const useTrends = () =>
  useQuery({ queryKey: queryKeys.trends, queryFn: getTrends, refetchInterval: POLL_INTERVAL })

export const useTopics = () =>
  useQuery({ queryKey: queryKeys.topics, queryFn: getTopics, refetchInterval: POLL_INTERVAL })

export const useNetwork = () =>
  useQueries({
    queries: [
      queryOptions({ queryKey: queryKeys.networkSummary, queryFn: getNetworkSummary, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.networkGraph, queryFn: () => getNetworkGraph(500), refetchInterval: POLL_INTERVAL }),
    ],
  })

export const useSystem = () => useQueries({ queries: [healthQuery, jobsQuery] })

export function useTimelineData() {
  return useQueries({
    queries: [
      queryOptions({
        queryKey: queryKeys.enrichedEvents({ limit: 50, newest_first: true }),
        queryFn: () => getEnrichedEvents({ limit: 50, newest_first: true }),
        refetchInterval: LIVE_POLL_INTERVAL,
      }),
      queryOptions({ queryKey: queryKeys.sentiment, queryFn: getSentiment, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.trends, queryFn: getTrends, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.networkSummary, queryFn: getNetworkSummary, refetchInterval: POLL_INTERVAL }),
      queryOptions({ queryKey: queryKeys.networkGraph, queryFn: () => getNetworkGraph(50), refetchInterval: POLL_INTERVAL }),
    ],
  })
}

export const useDemographics = () =>
  useQuery({ queryKey: queryKeys.demographics, queryFn: getDemographics, refetchInterval: POLL_INTERVAL })

export const useNetworkTemporal = (window = '1h') =>
  useQuery({
    queryKey: queryKeys.networkTemporal(window),
    queryFn: () => getNetworkTemporal(window, 6),
    refetchInterval: POLL_INTERVAL,
  })

export const useNetworkInfluence = () =>
  useQuery({ queryKey: queryKeys.networkInfluence, queryFn: () => getNetworkInfluence('pagerank', 10), refetchInterval: POLL_INTERVAL })

export const useNetworkCommunities = () =>
  useQuery({ queryKey: queryKeys.networkCommunities, queryFn: () => getNetworkCommunities(), refetchInterval: POLL_INTERVAL })

export const useNetworkCascades = () =>
  useQuery({ queryKey: queryKeys.networkCascades, queryFn: getNetworkCascades, refetchInterval: POLL_INTERVAL })

export const useNetworkCascade = (cascadeId: string | null) =>
  useQuery({
    queryKey: queryKeys.networkCascade(cascadeId ?? 'none'),
    queryFn: () => getNetworkCascade(cascadeId as string),
    enabled: cascadeId != null,
    refetchInterval: POLL_INTERVAL,
  })
