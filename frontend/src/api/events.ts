import { apiRequest, queryString } from './client'
import type {
  EnrichedEvent,
  EnrichedEventListResponse,
  EventListResponse,
  LiveEventsResponse,
} from '../types/events'

export interface EventQuery {
  [key: string]: string | number | boolean | undefined
  limit?: number
  offset?: number
  platform?: string
  q?: string
  sentiment?: string
  emotion?: string
  interaction?: string
  newest_first?: boolean
}

export const getEvents = (query: EventQuery = {}) =>
  apiRequest<EventListResponse>(`/events${queryString(query)}`)

export const getEnrichedEvents = (query: EventQuery = {}) =>
  apiRequest<EnrichedEventListResponse>(`/events/enriched${queryString(query)}`)

export const getEnrichedEvent = (eventId: string) =>
  apiRequest<EnrichedEvent>(`/events/${encodeURIComponent(eventId)}/enriched`)

export const getLiveEvents = (limit = 25) =>
  apiRequest<LiveEventsResponse>(`/events/live${queryString({ limit })}`)
