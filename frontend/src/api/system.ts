import { apiRequest } from './client'
import type { HealthResponse, SchedulerStatus } from '../types/system'

export const getHealth = () => apiRequest<HealthResponse>('/health')
export const getJobs = () => apiRequest<SchedulerStatus>('/system/jobs')

