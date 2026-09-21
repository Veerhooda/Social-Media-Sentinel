import { describe, expect, it } from 'vitest'
import { healthQuery, LIVE_POLL_INTERVAL, POLL_INTERVAL, SYSTEM_POLL_INTERVAL } from './useApiQueries'

describe('central polling policy', () => {
  it('uses shared, non-aggressive refresh intervals', () => {
    expect(POLL_INTERVAL).toBe(30_000)
    expect(SYSTEM_POLL_INTERVAL).toBe(10_000)
    expect(LIVE_POLL_INTERVAL).toBe(5_000)
    expect(healthQuery.refetchInterval).toBe(SYSTEM_POLL_INTERVAL)
  })
})
