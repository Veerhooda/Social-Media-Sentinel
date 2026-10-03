import { apiRequest, queryString } from './client'
import type {
  CascadeDetail,
  CascadeListResponse,
  CommunityListResponse,
  InfluenceResponse,
  NetworkGraphResponse,
  NetworkResponse,
  TemporalNetworkResponse,
} from '../types/network'

export const getNetworkSummary = () => apiRequest<NetworkResponse>('/network/summary')
export const getNetworkGraph = (limit = 500) =>
  apiRequest<NetworkGraphResponse>(`/network/graph${queryString({ limit })}`)


export const getNetworkTemporal = (window = '1h', count = 6) =>
  apiRequest<TemporalNetworkResponse>(`/network/temporal${queryString({ window, count })}`)
export const getNetworkInfluence = (metric = 'pagerank', limit = 20) =>
  apiRequest<InfluenceResponse>(`/network/influence${queryString({ metric, limit })}`)
export const getNetworkCommunities = (limit = 500) =>
  apiRequest<CommunityListResponse>(`/network/communities${queryString({ limit })}`)
export const getNetworkCascades = () => apiRequest<CascadeListResponse>('/network/cascades')
export const getNetworkCascade = (cascadeId: string) =>
  apiRequest<CascadeDetail>(`/network/cascades/${encodeURIComponent(cascadeId)}`)
