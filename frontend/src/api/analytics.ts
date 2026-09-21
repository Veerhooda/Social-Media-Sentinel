import { apiRequest } from './client'
import type {
  DemographicsResponse,
  TemporalSeriesResponse,
  TopicDetail,
  TopicEvolutionResponse,
  TopicListResponse,
  TrendAnalyticsResponse,
} from '../types/analytics'

export const getSentiment = () => apiRequest<TemporalSeriesResponse>('/analytics/sentiment')
export const getEmotions = () => apiRequest<TemporalSeriesResponse>('/analytics/emotions')
export const getTrends = () => apiRequest<TrendAnalyticsResponse>('/analytics/trends')
export const getTopics = () => apiRequest<TopicListResponse>('/analytics/topics')
export const getTopic = (topicId: number) =>
  apiRequest<TopicDetail>(`/analytics/topics/${topicId}`)
export const getTopicEvolution = (topicId: number) =>
  apiRequest<TopicEvolutionResponse>(`/analytics/topics/${topicId}/evolution`)

export const getDemographics = () =>
  apiRequest<DemographicsResponse>('/analytics/demographics')
